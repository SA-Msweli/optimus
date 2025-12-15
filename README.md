# Optimus - DeFi Banking Application

> **🚀 A comprehensive DeFi banking platform built on Aptos blockchain**  
> **🌐 Live Demo Coming Soon**

Optimus is a production-ready DeFi banking application that delivers institutional-grade financial services on the Aptos ecosystem.

## 🌟 Features

### Core DeFi Services

- **🔐 Decentralized Identity (DID)** - On-chain identity management with metadata support
- **💸 P2P Payments** - Instant token transfers with real-time address validation
- **🏦 Lending Protocol** - P2P lending with automated scheduled payments and collateral management
- **🌾 Yield Vaults** - Automated yield generation with strategy optimization
- **💱 DEX Trading** - Token trading with optimal capital efficiency

### Advanced Features

- **🔄 Automated Strategies** - Smart contract automation for yield optimization
- **📱 Mobile-First Design** - Responsive interface optimized for mobile DeFi

## 🏗️ Architecture

### Smart Contracts (Move)

- **DID Registry** (`did.move`) - Identity management and metadata storage
- **Lending Protocol** (`lending.move`) - P2P lending with automated payments
- **Yield Vaults** (`vault.move`) - Automated yield farming strategies
- **Stake Pool** (`stake_pool.move`) - Staking and rewards distribution

### Frontend Stack

- **React 18** with TypeScript for type-safe development
- **Vite** for fast development and optimized builds
- **Tailwind CSS + shadcn/ui** for modern, responsive design
- **React Query** for efficient state management and caching

### Blockchain Integration

- **Aptos TS SDK v5.0** for blockchain interactions
- **Wallet Adapter** supporting Petra, Martian, and Pontem wallets

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Aptos CLI (installed via npm)
- Supported wallet (Petra, Martian, or Pontem)

### Installation

1. **Clone and install dependencies:**

   ```bash
   git clone <repository-url>
   cd optimus
   npm install
   ```

2. **Set up environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Compile and deploy contracts:**

   ```bash
   npm run move:compile
   npm run move:publish
   ```

4. **Start the development server:**

   ```bash
   npm run dev
   ```

5. **Open your browser:**
   Navigate to `http://localhost:5173`

## 🌐 Deployment

Optimus can be deployed to various hosting platforms:

- **Vercel**: Optimized for Next.js/Vite applications
- **Netlify**: Static site hosting with edge functions
- **Traditional hosting**: Any platform supporting Node.js applications

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Project Configuration
PROJECT_NAME=optimus
VITE_APP_NETWORK=testnet

# Aptos Configuration
VITE_APTOS_API_KEY=your_aptos_api_key_here
VITE_MODULE_ADDRESS=your_deployed_module_address_here


```

## 📜 Available Scripts

### Move Contract Commands

- `npm run move:compile` - Compile Move contracts
- `npm run move:test` - Run Move unit tests
- `npm run move:publish` - Deploy contracts to blockchain
- `npm run move:upgrade` - Upgrade existing contracts

### Development Commands

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run build:check` - Type-check and build
- `npm run preview` - Preview production build

### Deployment Commands

- `npm run deploy` - Deploy to Vercel
- `npm run deploy:contracts` - Deploy contracts with validation
- `npm run deploy:status` - Check deployment status

### Testing & Quality

- `npm run test:integration` - Run integration tests
- `npm run lint` - Run ESLint
- `npm run fmt` - Format code with Prettier

## 🎯 Usage

### For Users

1. **Connect Wallet** - Use Petra, Martian, or Pontem wallet
2. **Create DID Profile** - Set up your on-chain identity
3. **Explore DeFi Features**:
   - Send P2P payments with address validation
   - Lend or borrow tokens with automated payments
   - Deposit to yield vaults for automated returns
   - Trade tokens with optimal capital efficiency

### For Developers

1. **Smart Contract Development** - Extend Move contracts in `contract/sources/`
2. **Frontend Development** - Build React components in `frontend/`
3. **Integration** - Add new DeFi protocols or external APIs
4. **Testing** - Write tests and use the integration test suite



## 🛠️ Technical Details

### Contract Addresses (Testnet)

- **Module Address**: `0xc367c4aefe1bc6028e0a5981c63c85347fcde2547f487904addc6762f8b130de`
- **Network**: Aptos Testnet
- **Deployment Status**: ✅ Live and operational

### Key Dependencies

- `@aptos-labs/ts-sdk`: Aptos blockchain integration
- `@radix-ui/*`: Accessible UI components
- `@tanstack/react-query`: Efficient data fetching and caching

## 📚 Documentation

- **Main README** - This file (project overview and setup)
- **Contract Docs** - Inline documentation in Move files
- **API Integration** - Service layer documentation in `frontend/services/`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **💻 Local Development**: Run `npm run dev` for local setup
- **🔍 Aptos Network**: [Aptos Testnet Explorer](https://explorer.aptoslabs.com/?network=testnet)

---

**Built with ❤️ for the Aptos ecosystem**
