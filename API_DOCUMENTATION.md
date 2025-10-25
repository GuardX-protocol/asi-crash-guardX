# GuardX Crypto Monitor API Documentation

## Overview
GuardX is a comprehensive cryptocurrency crash detection and monitoring system with AI-powered analysis, multi-channel notifications, and real-time price monitoring.

**Base URL**: `https://asi-crash-guard-x.vercel.app`  
**API Version**: 2.0.0  
**Authentication**: None required for most endpoints  

---

## 🏠 System Endpoints

### GET `/`
**Description**: Root endpoint with basic service information  
**Response**:
```json
{
  "status": "online",
  "service": "GuardX Crash Sentinel API",
  "version": "2.0.0",
  "platform": "vercel",
  "telegram_bot": "@guardx_detector_bot"
}
```

### GET `/health`
**Description**: Health check endpoint  
**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-25T19:30:00.000Z"
}
```

### GET `/system/status`
**Description**: Comprehensive system status including all services  
**Response**:
```json
{
  "system": {
    "status": "operational",
    "timestamp": "2025-10-25T19:30:00.000Z"
  },
  "database": {
    "status": "connected",
    "mongodb_url_configured": true
  },
  "telegram": {
    "bot_configured": true,
    "webhook_endpoint": "/telegram/webhook"
  },
  "monitoring": {
    "service_available": true,
    "status": {
      "running": true,
      "active_monitors": 5,
      "symbols_monitored": 15
    }
  },
  "ai_services": {
    "asi_configured": true,
    "email_configured": true
  },
  "environment": {
    "platform": "vercel"
  }
}
```

---

## 👤 User Management (`/users`)

### POST `/users/`
**Description**: Create a new user  
**Request Body**:
```json
{
  "walletAddress": "0x1234567890abcdef1234567890abcdef12345678",
  "email": "user@example.com",
  "telegramId": "123456789",
  "username": "crypto_user",
  "firstName": "John",
  "lastName": "Doe",
  "languageCode": "en",
  "notificationPreferences": {
    "telegram_alerts": true,
    "email_alerts": false,
    "webhook_alerts": false
  }
}
```
**Response**: User object with generated ID and timestamps

### GET `/users/{wallet_address}`
**Description**: Get user by wallet address  
**Parameters**:
- `wallet_address` (path): User's wallet address
**Response**: Complete user object with monitors and preferences

### GET `/users/`
**Description**: Get all users (paginated)  
**Query Parameters**:
- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Maximum records to return (default: 100)
**Response**: Array of user objects

### PATCH `/users/{wallet_address}`
**Description**: Partially update user (recommended for most updates)  
**Request Body** (all fields optional):
```json
{
  "email": "newemail@example.com",
  "firstName": "UpdatedName",
  "notificationPreferences": {
    "email_alerts": true
  }
}
```
**Features**:
- ✅ Email format validation
- ✅ Only updates provided fields
- ✅ Automatic timestamp updates

### PUT `/users/{wallet_address}`
**Description**: Full user update (replaces all fields)  
**Request Body**: Complete user object

### DELETE `/users/{wallet_address}`
**Description**: Delete user account  
**Response**: Confirmation message

### GET `/users/{wallet_address}/profile`
**Description**: Get detailed user profile with statistics  
**Response**:
```json
{
  "user": { /* user object */ },
  "statistics": {
    "total_monitors": 3,
    "active_monitors": 2,
    "total_alerts": 15,
    "recent_alerts": 5
  },
  "preferences": { /* notification preferences */ },
  "account_age_days": 30
}
```

### PATCH `/users/{wallet_address}/preferences`
**Description**: Update notification preferences  
**Request Body**:
```json
{
  "telegram_alerts": true,
  "email_alerts": true,
  "webhook_alerts": false
}
```

---

## 📊 Monitor Management (`/monitors`)

### POST `/monitors/`
**Description**: Create a new monitor  
**Query Parameters**:
- `user_id` (required): User's wallet address or ID
**Request Body**:
```json
{
  "name": "My BTC Monitor",
  "symbols": ["BTC", "ETH"],
  "crash_threshold": 5.0,
  "enabled": true,
  "notification_channels": ["telegram", "email"]
}
```
**Response**: Monitor object with ID and metadata
**Features**:
- ✅ Automatic USDT suffix addition
- ✅ User validation
- ✅ Background notifications
- ✅ Updates user.monitors array

### GET `/monitors/`
**Description**: Get all monitors for a user  
**Query Parameters**:
- `user_id` (required): User's wallet address or ID
**Response**: Array of monitor objects with alert counts

### GET `/monitors/{monitor_id}`
**Description**: Get specific monitor details  
**Query Parameters**:
- `user_id` (required): User's wallet address for authorization
**Response**: Detailed monitor object with alert count

### PATCH `/monitors/{monitor_id}`
**Description**: Update monitor (partial update)  
**Query Parameters**:
- `user_id` (required): User's wallet address for authorization
**Request Body** (all fields optional):
```json
{
  "name": "Updated Monitor Name",
  "symbols": ["BTC", "ETH", "ADA"],
  "crash_threshold": 3.0,
  "enabled": false,
  "notification_channels": ["telegram"]
}
```
**Features**:
- ✅ Syncs with user.monitors array
- ✅ Symbol validation and formatting

### DELETE `/monitors/{monitor_id}`
**Description**: Delete monitor  
**Query Parameters**:
- `user_id` (required): User's wallet address for authorization
**Features**:
- ✅ Deletes associated alerts
- ✅ Updates user.monitors array

### POST `/monitors/{monitor_id}/toggle`
**Description**: Toggle monitor enabled/disabled status  
**Query Parameters**:
- `user_id` (required): User's wallet address for authorization
**Response**:
```json
{
  "message": "Monitor enabled successfully",
  "enabled": true
}
```

### GET `/monitors/{monitor_id}/alerts`
**Description**: Get alerts for a specific monitor  
**Query Parameters**:
- `user_id` (required): User's wallet address for authorization
- `limit` (optional): Maximum alerts to return (default: 50)
- `skip` (optional): Number of alerts to skip (default: 0)
**Response**:
```json
{
  "monitor_id": "monitor_id",
  "monitor_name": "Monitor Name",
  "alerts": [
    {
      "id": "alert_id",
      "symbol": "BTCUSDT",
      "crash_probability": 0.85,
      "current_price": 42000.0,
      "price_drop": 7.5,
      "analysis": "AI analysis text",
      "createdAt": "2025-10-25T19:30:00.000Z",
      "notification_sent": true
    }
  ],
  "total_alerts": 1
}
```

### GET `/monitors/stats/summary`
**Description**: Get monitoring statistics for a user  
**Query Parameters**:
- `user_id` (required): User's wallet address
**Response**:
```json
{
  "total_monitors": 3,
  "active_monitors": 2,
  "inactive_monitors": 1,
  "total_symbols": 8,
  "recent_alerts_7d": 12,
  "monitors": [
    {
      "id": "monitor_id",
      "name": "Monitor Name",
      "symbols_count": 3,
      "enabled": true,
      "last_updated": "2025-10-25T19:30:00.000Z"
    }
  ]
}
```

---

## 💰 Cryptocurrency Data (`/crypto`)

### GET `/crypto/prices`
**Description**: Get cryptocurrency prices  
**Query Parameters**:
- `symbols` (optional): Comma-separated list of symbols (e.g., "BTC,ETH,ADA")
- `limit` (optional): Limit number of results
**Response**:
```json
{
  "BTCUSDT": {
    "symbol": "BTCUSDT",
    "price": 45000.0,
    "change_24h": 2.5,
    "volume_24h": 1000000.0,
    "market_cap": null,
    "timestamp": "2025-10-25T19:30:00.000Z"
  }
}
```

### GET `/crypto/prices/{symbol}`
**Description**: Get single cryptocurrency price  
**Parameters**:
- `symbol` (path): Cryptocurrency symbol (automatically adds USDT if needed)
**Response**: TokenPrice object
**Features**:
- ✅ Multiple API fallbacks (Binance, CoinGecko)
- ✅ Automatic USDT suffix
- ✅ Geo-blocking handling

### GET `/crypto/prices/realtime/{symbol}`
**Description**: Get real-time price with trend analysis  
**Response**:
```json
{
  "symbol": "BTCUSDT",
  "current_price": 45000.0,
  "change_24h": 2.5,
  "volume_24h": 1000000.0,
  "high_24h": 46000.0,
  "low_24h": 44000.0,
  "trend": "bullish",
  "recent_candles": 10,
  "last_update": "2025-10-25T19:30:00.000Z",
  "source": "binance_realtime"
}
```

### GET `/crypto/prices/mock/{symbol}`
**Description**: Get mock prices for testing  
**Response**: Mock TokenPrice object for common symbols

### GET `/crypto/prices/test-sources/{symbol}`
**Description**: Test all available price sources for a symbol  
**Response**:
```json
{
  "symbol": "BTCUSDT",
  "working_sources": 2,
  "total_sources": 3,
  "sources": {
    "binance_1": {
      "status": "✅ Available",
      "price": 45000.0,
      "source": "api.binance.com"
    }
  },
  "recommendation": "External APIs available"
}
```

### GET `/crypto/binance/test`
**Description**: Test Binance API connectivity and performance  
**Response**: Detailed performance metrics and cache statistics

### GET `/crypto/alerts`
**Description**: Get alerts with filtering  
**Query Parameters**:
- `user_id` (optional): Filter by user
- `symbol` (optional): Filter by symbol
- `severity` (optional): Filter by severity
- `limit` (optional): Maximum results (default: 100)
**Response**: Array of alert objects

---

## 📱 Telegram Integration (`/telegram`)

### POST `/telegram/send`
**Description**: Send Telegram message  
**Request Body**:
```json
{
  "telegram_id": "123456789",
  "message": "Your message here",
  "parse_mode": "Markdown"
}
```
**Response**:
```json
{
  "success": true,
  "message": "Message sent successfully",
  "timestamp": "2025-10-25T19:30:00.000Z"
}
```

### POST `/telegram/test`
**Description**: Test Telegram bot configuration  
**Response**:
```json
{
  "configured": true,
  "bot_info": { /* bot details */ },
  "message": "Telegram bot is configured and working"
}
```

### GET `/telegram/status`
**Description**: Get Telegram integration status  
**Response**:
```json
{
  "telegram_configured": true,
  "bot_token_present": true,
  "webhook_info": { /* webhook details */ },
  "api_endpoint": "https://api.telegram.org/bot<TOKEN>/sendMessage",
  "supported_parse_modes": ["Markdown", "HTML", null]
}
```

### POST `/telegram/send-alert`
**Description**: Send crash alert to user via Telegram  
**Request Body**:
```json
{
  "user_id": "wallet_address_or_telegram_id",
  "symbol": "BTCUSDT",
  "alert_type": "crash_detected",
  "crash_probability": 0.85,
  "price_change": -7.5,
  "current_price": 42000.0,
  "severity": "high",
  "additional_info": "AI analysis details"
}
```
**Features**:
- ✅ User preference checking
- ✅ Markdown formatting
- ✅ Severity-based styling

### GET `/telegram/users-with-alerts`
**Description**: Get all users with Telegram alerts enabled  
**Response**:
```json
{
  "total_users": 5,
  "users": [
    {
      "wallet_address": "0x123...",
      "telegram_id": "123456789",
      "username": "crypto_user",
      "first_name": "John",
      "is_active": true
    }
  ]
}
```

### POST `/telegram/webhook/setup`
**Description**: Setup Telegram webhook  
**Request Body**:
```json
{
  "webhook_url": "https://your-domain.com/telegram/webhook",
  "secret_token": "optional_secret"
}
```

### PATCH `/telegram/webhook`
**Description**: Update webhook settings  
**Request Body**:
```json
{
  "webhook_url": "https://new-domain.com/telegram/webhook",
  "enabled": true
}
```

### DELETE `/telegram/webhook`
**Description**: Delete/disable webhook

### POST `/telegram/webhook`
**Description**: Telegram webhook endpoint (receives updates from Telegram)  
**Request Body**: Telegram Update object
**Features**:
- ✅ Handles messages, edited messages, callback queries
- ✅ User registration and wallet setup
- ✅ Command processing (/start, /help, /status, etc.)
- ✅ Multi-step interactions

---

## 🔧 Legacy Crypto Endpoints (`/crypto`)

### POST `/crypto/monitor/create`
**Description**: Create monitor (legacy endpoint)  
**Request Body**: MonitorConfigRequest object

### GET `/crypto/monitors`
**Description**: List monitor configs (legacy)

### PATCH `/crypto/monitor/{monitor_name}`
**Description**: Update monitor by name (legacy)

### PUT `/crypto/monitor/{monitor_name}`
**Description**: Full monitor update by name (legacy)

### DELETE `/crypto/monitor/{monitor_name}`
**Description**: Delete monitor by name (legacy)

### GET `/crypto/monitor`
**Description**: Get monitor status (legacy)

### POST `/crypto/monitor/trigger`
**Description**: Manually trigger monitoring for testing

### PATCH `/crypto/alerts/{alert_id}`
**Description**: Update alert by ID

---

## 📊 Data Models

### User Model
```json
{
  "walletAddress": "string (unique)",
  "email": "string (optional)",
  "telegramId": "string (optional)",
  "username": "string (optional)",
  "firstName": "string (optional)",
  "lastName": "string (optional)",
  "languageCode": "string (default: 'en')",
  "isActive": "boolean (default: true)",
  "notificationPreferences": {
    "telegram_alerts": "boolean (default: true)",
    "email_alerts": "boolean (default: false)",
    "webhook_alerts": "boolean (default: false)"
  },
  "monitors": [
    {
      "id": "string",
      "name": "string",
      "enabled": "boolean",
      "created_at": "datetime",
      "symbols": ["string"]
    }
  ],
  "createdAt": "datetime",
  "updatedAt": "datetime",
  "lastLoginAt": "datetime (optional)"
}
```

### Monitor Model
```json
{
  "name": "string (unique)",
  "userId": "string (wallet address)",
  "symbols": ["string"],
  "crash_threshold": "float (1.0-50.0, default: 10.0)",
  "enabled": "boolean (default: true)",
  "notification_channels": ["string (telegram, email)"],
  "last_check": "datetime (optional)",
  "createdAt": "datetime",
  "updatedAt": "datetime"
}
```

### MonitorAlert Model
```json
{
  "monitorId": "string",
  "userId": "string (wallet address)",
  "symbol": "string",
  "token_name": "string",
  "crash_probability": "float (0-1)",
  "current_price": "float",
  "price_drop": "float (percentage)",
  "price_before_crash": "float (optional)",
  "analysis": "string (formatted AI analysis)",
  "crash_detected_at": "datetime",
  "notification_sent": "boolean",
  "notification_channels": ["string"],
  "telegram_sent": "boolean",
  "email_sent": "boolean",
  "webhook_sent": "boolean",
  "technical_indicators": "object",
  "asi_analysis": "string (raw AI analysis, optional)",
  "confidence_level": "string (low, medium, high, very_high)",
  "createdAt": "datetime"
}
```

---

## 🚀 Key Features

### AI-Powered Analysis
- **ASI-1 Fast Integration**: Advanced AI crash detection
- **Technical Indicators**: RSI, MACD, Bollinger Bands, Volume analysis
- **Formatted Responses**: Structured AI analysis for emails and alerts

### Multi-Channel Notifications
- **Telegram**: Real-time bot notifications with rich formatting
- **Email**: HTML formatted alerts with AI analysis
- **Webhook**: Programmable notifications (coming soon)

### Real-Time Monitoring
- **24/7 Monitoring**: Continuous price and market monitoring
- **Multiple Exchanges**: Binance, CoinGecko fallbacks
- **Crash Detection**: Configurable thresholds and probability scoring

### User Management
- **Wallet Integration**: Support for Ethereum, Bitcoin, Solana, TON
- **Flexible Preferences**: Granular notification controls
- **Monitor References**: Structured monitor tracking in user profiles

### Database Features
- **MongoDB**: Scalable document storage
- **Comprehensive Indexing**: Optimized queries for users, monitors, alerts
- **Alert History**: Complete audit trail of all notifications

---

## 🔐 Security & Best Practices

### Authentication
- **Wallet-Based**: Users identified by wallet addresses
- **Telegram Integration**: Secure bot token authentication
- **No API Keys Required**: Public endpoints for most functionality

### Data Validation
- **Email Validation**: Regex-based email format checking
- **Wallet Validation**: Multi-format crypto address validation
- **Input Sanitization**: Protection against malicious inputs

### Error Handling
- **Graceful Degradation**: Fallback mechanisms for external APIs
- **Detailed Error Messages**: Clear error responses for debugging
- **Database Resilience**: Connection retry and error recovery

---

## 📈 Usage Examples

### Frontend Integration Examples

#### Create User and Monitor
```javascript
// 1. Create user
const user = await fetch('/users/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    walletAddress: '0x1234567890abcdef1234567890abcdef12345678',
    email: 'user@example.com',
    firstName: 'John',
    notificationPreferences: {
      telegram_alerts: true,
      email_alerts: true
    }
  })
});

// 2. Create monitor
const monitor = await fetch('/monitors/?user_id=0x1234567890abcdef1234567890abcdef12345678', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'My Crypto Monitor',
    symbols: ['BTC', 'ETH'],
    crash_threshold: 5.0,
    notification_channels: ['telegram', 'email']
  })
});
```

#### Get User Dashboard Data
```javascript
// Get user profile with statistics
const profile = await fetch('/users/0x1234567890abcdef1234567890abcdef12345678/profile');

// Get user's monitors
const monitors = await fetch('/monitors/?user_id=0x1234567890abcdef1234567890abcdef12345678');

// Get recent alerts
const alerts = await fetch('/crypto/alerts?user_id=0x1234567890abcdef1234567890abcdef12345678&limit=10');
```

#### Real-Time Price Display
```javascript
// Get multiple prices
const prices = await fetch('/crypto/prices?symbols=BTC,ETH,ADA');

// Get single price with trend
const btcPrice = await fetch('/crypto/prices/realtime/BTC');
```

### Mobile App Integration
```javascript
// Enable notifications
await fetch('/users/0x123.../preferences', {
  method: 'PATCH',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    telegram_alerts: true,
    email_alerts: true
  })
});

// Toggle monitor
await fetch('/monitors/monitor_id/toggle?user_id=0x123...', {
  method: 'POST'
});
```

---

## 🛠️ Development Notes

### Environment Variables Required
```env
MONGODB_URL=mongodb://...
TELEGRAM_BOT_TOKEN=bot_token
ASI_API_KEY=asi_api_key
EMAIL_USER=smtp_user
EMAIL_PASSWORD=smtp_password
```

### Rate Limits
- **Price APIs**: Cached for 60 seconds
- **Telegram API**: Respects Telegram limits
- **Database**: No artificial limits

### Deployment
- **Platform**: Vercel serverless
- **Database**: MongoDB Atlas
- **Monitoring**: Built-in health checks

This API provides a complete cryptocurrency monitoring and alerting system with AI-powered analysis, multi-channel notifications, and comprehensive user management. Perfect for building crypto portfolio management applications, trading bots, or investment monitoring dashboards.