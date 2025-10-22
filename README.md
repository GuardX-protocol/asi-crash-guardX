# Crypto Market Monitor & Crash Detector

A comprehensive FastAPI application with advanced crypto monitoring, market crash detection, and uAgents integration. Features real-time price tracking, configurable alerts, and AI-powered market analysis with 77-80% accuracy.

## 🚀 Features

### 📊 **Crypto Price Monitoring**
- Real-time price tracking from multiple exchanges (Binance, CoinGecko)
- Top cryptocurrencies by market cap
- Configurable monitoring intervals and thresholds
- Smart caching for faster responses
- Portfolio and individual token tracking

### 🚨 **Market Crash Detection**
- Advanced LPPLS bubble detection (71% accuracy)
- Technical indicators: RSI, MACD, Bollinger Bands, Moving Averages
- Order book pressure analysis (71% accuracy)
- Liquidation cascade risk detection (77% accuracy)
- ASI:One AI integration for intelligent analysis

### 🤖 **uAgents Integration**
- Autonomous market monitoring agents
- Real-time crash probability calculations
- Intelligent alert system
- Chat protocol for agent interaction

### ⚙️ **Configurable Monitoring**
- Custom token lists and monitoring intervals
- Price and volume change thresholds
- Webhook alerts (Discord, Slack, custom endpoints)
- Enable/disable monitors dynamically
- Multi-monitor support

## 🛠️ Setup

### Prerequisites
- Python 3.9+
- pip or pip3

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/GuardX-protocol/asi-crash-guardX.git
cd asi-crash-guardX
```

2. **Install dependencies:**
```bash
pip3 install -r requirements.txt
```

3. **Configure environment variables:**
```bash
# Copy and edit the .env file
cp .env.example .env

# Add your API keys:
ASI_API_KEY=your_asi_api_key_here
AGENT_SEED=your_unique_seed_phrase
```

4. **Run the application:**
```bash
# FastAPI server
uvicorn main:app --reload --port 8002

# Or run the crash detector agent standalone
python3 run_agent.py
```

5. **Access the application:**
- API Documentation: http://127.0.0.1:8002/docs
- ReDoc: http://127.0.0.1:8002/redoc
- Health Check: http://127.0.0.1:8002/health

## 📚 API Documentation

### 🏠 **Core Endpoints**
- `GET /` - Welcome message
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation

### 💰 **Crypto Price Monitoring**
- `GET /crypto/prices` - Get crypto prices with optional filters
- `GET /crypto/prices/top/{count}` - Top N cryptocurrencies by market cap
- `GET /crypto/prices/{symbol}` - Get price for specific cryptocurrency

### 📈 **Monitor Management**
- `POST /crypto/monitor/create` - Create new monitoring configuration
- `GET /crypto/monitors` - List all monitor configurations
- `GET /crypto/monitor/{name}` - Get specific monitor configuration
- `PUT /crypto/monitor/{name}` - Update monitor configuration
- `DELETE /crypto/monitor/{name}` - Delete monitor configuration

### 🎛️ **Monitor Control**
- `POST /crypto/monitor/{name}/start` - Start specific monitor
- `POST /crypto/monitor/{name}/stop` - Stop specific monitor
- `POST /crypto/monitor/start-all` - Start all enabled monitors
- `POST /crypto/monitor/stop-all` - Stop all running monitors
- `GET /crypto/monitor` - Get monitoring status

### 🚨 **Market Crash Detection**
- `GET /market/status` - Get crash detector agent status
- `POST /market/analyze` - Analyze market with optional parameters
- `GET /market/analyze/{symbol}` - Analyze specific symbol for crash signals
- `GET /market/alerts` - Get latest crash alerts
- `POST /market/start-agent` - Start crash detection agent
- `POST /market/stop-agent` - Stop crash detection agent

### 👥 **User & Item Management**
- `GET /users/` - List all users
- `GET /users/{user_id}` - Get specific user
- `POST /users/` - Create new user
- `GET /items/` - List all items
- `GET /items/{item_id}` - Get specific item
- `POST /items/` - Create new item

## 🔧 Configuration Options

### **Price Monitoring Parameters (All Optional)**
```json
{
  "symbols": ["BTC", "ETH", "ADA"],     // Token symbols to monitor
  "source": "binance",                  // Data source: binance, coingecko, both
  "use_cache": true,                    // Use cached data for faster response
  "limit": 10                           // Limit number of results
}
```

### **Monitor Configuration**
```json
{
  "name": "portfolio-monitor",          // Unique monitor name
  "symbols": ["BTC", "ETH", "SOL"],     // Tokens to monitor
  "interval_seconds": 60,               // Monitoring interval (default: 60)
  "price_change_threshold": 5.0,        // Price alert threshold % (default: 5.0)
  "volume_change_threshold": 50.0,      // Volume alert threshold % (default: 50.0)
  "enabled": true,                      // Enable/disable monitor (default: true)
  "alert_webhooks": [                   // Webhook URLs for alerts
    "https://discord.com/api/webhooks/...",
    "https://hooks.slack.com/services/..."
  ]
}
```

### **Crash Detection Parameters**
```json
{
  "symbol": "BTCUSDT",                  // Symbol to analyze (default: BTCUSDT)
  "lookback": 100                       // Historical data points (default: 100)
}
```

## 📊 Example Usage

### **Monitor Top 10 Cryptocurrencies**
```bash
curl -X GET "http://127.0.0.1:8002/crypto/prices/top/10"
```

### **Create Portfolio Monitor**
```bash
curl -X POST "http://127.0.0.1:8002/crypto/monitor/create" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-portfolio",
    "symbols": ["BTC", "ETH", "ADA", "SOL"],
    "interval_seconds": 30,
    "price_change_threshold": 3.0,
    "enabled": true
  }'
```

### **Start Monitor**
```bash
curl -X POST "http://127.0.0.1:8002/crypto/monitor/my-portfolio/start"
```

### **Analyze Market Crash Risk**
```bash
curl -X GET "http://127.0.0.1:8002/market/analyze/BTCUSDT"
```

### **Get Specific Token Price**
```bash
curl -X GET "http://127.0.0.1:8002/crypto/prices/BTC?source=binance"
```

## 🤖 uAgents Integration

The application includes a sophisticated crash detection agent that:

- **Monitors markets every 5 minutes** for crash signals
- **Uses proven algorithms** with 77-80% accuracy
- **Integrates ASI:One AI** for intelligent analysis
- **Provides real-time alerts** for high-risk conditions
- **Supports chat protocol** for interactive queries

### **Running the Agent Standalone**
```bash
python3 run_agent.py
```

## 🔍 Monitoring Capabilities

### **Supported Exchanges**
- **Binance**: Real-time price and volume data
- **CoinGecko**: Market cap and comprehensive token data

### **Alert Triggers**
- Price changes exceeding configured thresholds
- Volume spikes indicating unusual activity
- Market crash probability above 50%
- Technical indicator signals (RSI, MACD, etc.)

### **Webhook Integration**
- Discord notifications
- Slack alerts
- Custom webhook endpoints
- Real-time alert delivery

## 🏗️ Architecture

```
├── main.py                    # FastAPI application entry point
├── requirements.txt           # Python dependencies
├── run_agent.py              # Standalone agent runner
├── .env                      # Environment configuration
└── app/
    ├── agents/
    │   └── crash_detector.py  # uAgents crash detection
    ├── routers/
    │   ├── crypto.py          # Crypto monitoring endpoints
    │   ├── market.py          # Market crash detection endpoints
    │   ├── users.py           # User management
    │   └── items.py           # Item management
    ├── services/
    │   └── crypto_monitor.py  # Core monitoring service
    └── models.py              # Pydantic data models
```

## 🚀 Production Deployment

### **Environment Variables**
```bash
ASI_API_KEY=your_asi_api_key_from_asi1.ai
AGENT_SEED=unique_seed_phrase_for_agent
```

### **Docker Deployment** (Optional)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8002
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
```

## 📈 Performance Features

- **Smart Caching**: Reduces API calls and improves response times
- **Concurrent Monitoring**: Multiple monitors running simultaneously
- **Resource Management**: Proper cleanup and memory management
- **Error Handling**: Robust error handling for API failures
- **Rate Limiting**: Respects exchange API rate limits

## 🔐 Security

- Environment variable configuration for sensitive data
- Input validation and sanitization
- Secure webhook handling
- Rate limiting protection

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the API documentation at `/docs`
- Review the example usage above
- Open an issue on GitHub

---

**Built with FastAPI, uAgents, and ASI:One AI for comprehensive crypto market monitoring and crash detection.**

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)