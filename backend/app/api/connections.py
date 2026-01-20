"""Connections API routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from app.database import get_db
from app.models import Connection
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionUpdate,
    ConnectionResponse,
    ConnectionTestResult,
)
from app.core.security import encrypt_password, decrypt_password
from app.services.qbittorrent import QBittorrentService

router = APIRouter()


@router.get("", response_model=List[ConnectionResponse])
async def list_connections(db: AsyncSession = Depends(get_db)):
    """List all connections."""
    result = await db.execute(select(Connection).order_by(Connection.type, Connection.name))
    connections = result.scalars().all()
    return connections


@router.post("", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    data: ConnectionCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new connection."""
    # Encrypt password if provided
    password = encrypt_password(data.password) if data.password else None

    connection = Connection(
        type=data.type.value,
        name=data.name,
        url=data.url.rstrip("/"),
        api_key=data.api_key,
        username=data.username,
        password=password,
        enabled=data.enabled,
    )
    db.add(connection)
    await db.commit()
    await db.refresh(connection)
    return connection


@router.get("/{connection_id}", response_model=ConnectionResponse)
async def get_connection(connection_id: int, db: AsyncSession = Depends(get_db)):
    """Get a connection by ID."""
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    return connection


@router.put("/{connection_id}", response_model=ConnectionResponse)
async def update_connection(
    connection_id: int, data: ConnectionUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a connection."""
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    update_data = data.model_dump(exclude_unset=True)

    # Handle type conversion
    if "type" in update_data and update_data["type"]:
        update_data["type"] = update_data["type"].value

    # Handle password encryption
    if "password" in update_data:
        if update_data["password"]:
            update_data["password"] = encrypt_password(update_data["password"])
        else:
            update_data["password"] = None

    # Handle URL
    if "url" in update_data and update_data["url"]:
        update_data["url"] = update_data["url"].rstrip("/")

    for key, value in update_data.items():
        setattr(connection, key, value)

    await db.commit()
    await db.refresh(connection)
    return connection


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(connection_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a connection."""
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    await db.delete(connection)
    await db.commit()


@router.post("/{connection_id}/test", response_model=ConnectionTestResult)
async def test_connection(connection_id: int, db: AsyncSession = Depends(get_db)):
    """Test a connection."""
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    if connection.type == "qbittorrent":
        qbt = QBittorrentService(
            url=connection.url,
            username=connection.username or "",
            password=decrypt_password(connection.password) if connection.password else "",
        )
        test_result = await qbt.test_connection()
        await qbt.disconnect()
        return ConnectionTestResult(**test_result)

    elif connection.type in ["sonarr", "radarr", "prowlarr"]:
        try:
            async with httpx.AsyncClient() as client:
                headers = {"X-Api-Key": connection.api_key}
                response = await client.get(
                    f"{connection.url}/api/v1/system/status",
                    headers=headers,
                    timeout=10,
                )
                response.raise_for_status()
                data = response.json()
                return ConnectionTestResult(
                    success=True,
                    message="Connected successfully",
                    details={"version": data.get("version")},
                )
        except httpx.HTTPStatusError as e:
            return ConnectionTestResult(
                success=False,
                message=f"HTTP error: {e.response.status_code}",
            )
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=str(e),
            )

    elif connection.type == "discord":
        # Test Discord webhook
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(connection.url, timeout=10)
                if response.status_code in [200, 401]:  # Webhook exists
                    return ConnectionTestResult(
                        success=True,
                        message="Webhook URL is valid",
                    )
                return ConnectionTestResult(
                    success=False,
                    message=f"Invalid webhook: HTTP {response.status_code}",
                )
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=str(e),
            )

    elif connection.type == "telegram":
        # Test Telegram bot
        try:
            bot_token = connection.url
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.telegram.org/bot{bot_token}/getMe",
                    timeout=10,
                )
                data = response.json()
                if data.get("ok"):
                    return ConnectionTestResult(
                        success=True,
                        message="Bot connected successfully",
                        details={"bot_name": data.get("result", {}).get("username")},
                    )
                return ConnectionTestResult(
                    success=False,
                    message=data.get("description", "Unknown error"),
                )
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=str(e),
            )

    return ConnectionTestResult(
        success=False,
        message=f"Unknown connection type: {connection.type}",
    )
