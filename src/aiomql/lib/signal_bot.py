import asyncio
import time
from typing import Callable, Iterable
import logging

from ..core.config import Config
from ..core.meta_trader import MetaTrader
from ..core.meta_backtester import MetaBackTester
from .symbol import Symbol as Symbol

logger = logging.getLogger(__name__)


class SignalBot:
    """Bot for detecting trading signals without executing trades.

    Attributes:
        config (Config): Config instance
        mt (MetaTrader): MetaTrader instance
        symbols (list[Symbol]): List of symbols to monitor
        signal_callbacks (dict): Dictionary of signal detection callbacks
        initialized (bool): Terminal initialization status
        login (bool): Login status
        monitoring (bool): Signal monitoring status
    """
    config: Config
    mt: MetaTrader
    symbols: list[Symbol]
    signal_callbacks: dict[Symbol, list[Callable]]
    initialized: bool
    login: bool
    monitoring: bool

    def __init__(self):
        self.config = Config(bot=self)
        self.mt5 = MetaTrader() if self.config.mode != "backtest" else MetaBackTester()
        self.symbols = []
        self.signal_callbacks = {}
        self.initialized = False
        self.login = False
        self.monitoring = False

    async def start_terminal(self):
        """Start terminal and login asynchronously"""
        res = await self.mt5.initialize()
        if res:
            self.initialized = True
            res = await self.mt5.login()
            if res:
                self.login = True
        return res

    def start_terminal_sync(self):
        """Start terminal and login synchronously"""
        res = self.mt5.initialize_sync()
        if res:
            self.initialized = True
            res = self.mt5.login_sync()
            if res:
                self.login = True
        return res

    async def initialize(self):
        """Prepares the bot by signing in to the trading account and initializing symbols for monitoring.

        Raises:
            SystemExit if sign_in was not successful
        """
        try:
            await self.start_terminal()
            if not self.login:
                logger.critical("Unable to sign in to MetaTrader 5 Terminal")
                raise Exception("Unable to sign in to MetaTrader 5 Terminal")
            logger.info("Login Successful")
            await self.init_symbols()
            
            if len(self.symbols) == 0:
                logger.warning("No symbols were added to the bot. Exiting in one second")
                await asyncio.sleep(1)
                self.config.shutdown = True
            else:
                logger.info(f"Signal detection bot initialized with {len(self.symbols)} symbols")
        except Exception as err:
            logger.error("%s: Signal bot initialization failed", err)
            raise SystemExit

    def initialize_sync(self):
        """Prepares the bot by signing in to the trading account and initializing symbols for monitoring.

        Raises:
            SystemExit if sign_in was not successful
        """
        try:
            self.start_terminal_sync()
            if not self.login:
                logger.critical("Unable to sign in to MetaTrader 5 Terminal")
                raise Exception("Unable to sign in to MetaTrader 5 Terminal")
            logger.info("Login Successful")
            self.init_symbols_sync()
            
            if len(self.symbols) == 0:
                logger.warning("No symbols were added to the bot. Exiting in one second")
                time.sleep(1)
                self.config.shutdown = True
            else:
                logger.info(f"Signal detection bot initialized with {len(self.symbols)} symbols")
        except Exception as err:
            logger.error("%s: Signal bot initialization failed", err)
            raise SystemExit

    def add_symbol(self, *, symbol: Symbol, callback: Callable = None):
        """Add a symbol to monitor for signals.

        Args:
            symbol (Symbol): A Symbol instance to monitor
            callback (Callable): Optional callback function to execute when signal detected
        """
        self.symbols.append(symbol)
        if callback:
            if symbol not in self.signal_callbacks:
                self.signal_callbacks[symbol] = []
            self.signal_callbacks[symbol].append(callback)

    def add_symbols(self, *, symbols: Iterable[Symbol], callback: Callable = None):
        """Add multiple symbols at the same time

        Args:
            symbols (Iterable[Symbol]): A list of symbols to monitor
            callback (Callable): Optional callback function to execute when signals detected
        """
        for symbol in symbols:
            self.add_symbol(symbol=symbol, callback=callback)

    async def init_symbol(self, *, symbol: Symbol) -> bool:
        """Initialize a single symbol. This method is called internally by the bot."""
        try:
            res = await symbol.initialize()
            if res:
                logger.info(f"Symbol {symbol.name} initialized successfully")
            else:
                logger.warning(f"Failed to initialize symbol {symbol.name}")
            return res
        except Exception as err:
            logger.error(f"Error initializing symbol {symbol.name}: {err}")
            return False

    async def init_symbols(self):
        """Initialize all symbols for monitoring. This method is called internally by the bot."""
        tasks = [self.init_symbol(symbol=symbol) for symbol in self.symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Remove symbols that failed to initialize
        self.symbols = [symbol for symbol, result in zip(self.symbols, results) if result is True]

    def init_symbol_sync(self, *, symbol: Symbol) -> bool:
        """Initialize a single symbol synchronously. This method is called internally by the bot."""
        try:
            res = symbol.initialize_sync()
            if res:
                logger.info(f"Symbol {symbol.name} initialized successfully")
            else:
                logger.warning(f"Failed to initialize symbol {symbol.name}")
            return res
        except Exception as err:
            logger.error(f"Error initializing symbol {symbol.name}: {err}")
            return False

    def init_symbols_sync(self):
        """Initialize all symbols for monitoring synchronously. This method is called internally by the bot."""
        results = [self.init_symbol_sync(symbol=symbol) for symbol in self.symbols]
        # Remove symbols that failed to initialize
        self.symbols = [symbol for symbol, result in zip(self.symbols, results) if result is True]

    async def detect_signals(self, *, symbol: Symbol):
        """Monitor a symbol and detect trading signals.

        Args:
            symbol (Symbol): Symbol to monitor
        """
        logger.info(f"Starting signal detection for {symbol.name}")
        
        while self.monitoring and not self.config.shutdown:
            try:
                # Get latest market data
                await symbol.update()
                
                # Check for signals (implement your signal logic here)
                signal = await self.check_signal(symbol=symbol)
                
                if signal:
                    logger.info(f"Signal detected for {symbol.name}: {signal}")
                    
                    # Execute callbacks if any
                    if symbol in self.signal_callbacks:
                        for callback in self.signal_callbacks[symbol]:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(symbol, signal)
                                else:
                                    callback(symbol, signal)
                            except Exception as err:
                                logger.error(f"Error executing callback for {symbol.name}: {err}")
                
                # Sleep before next check (configurable interval)
                await asyncio.sleep(self.config.signal_check_interval if hasattr(self.config, 'signal_check_interval') else 1)
                
            except Exception as err:
                logger.error(f"Error detecting signals for {symbol.name}: {err}")
                await asyncio.sleep(5)

    async def check_signal(self, *, symbol: Symbol) -> dict | None:
        """Check if there's a trading signal for the symbol.
        Override this method to implement your own signal detection logic.

        Args:
            symbol (Symbol): Symbol to check

        Returns:
            dict: Signal information if detected, None otherwise
            Example: {'type': 'BUY', 'price': 1.2345, 'strength': 0.8}
        """
        # Placeholder - implement your signal detection logic here
        # This is where you'd check technical indicators, patterns, etc.
        return None

    async def monitor_all_signals(self):
        """Monitor all symbols for signals concurrently."""
        self.monitoring = True
        logger.info("Starting signal monitoring for all symbols")
        
        tasks = [self.detect_signals(symbol=symbol) for symbol in self.symbols]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("Signal monitoring stopped")

    def stop_monitoring(self):
        """Stop monitoring signals."""
        self.monitoring = False
        logger.info("Stopping signal monitoring")

    async def start(self):
        """Initialize the bot and start signal monitoring."""
        await self.initialize()
        if self.config.shutdown is False and len(self.symbols) > 0:
            await self.monitor_all_signals()

    def execute(self):
        """Start the bot in sync mode and monitor signals."""
        self.initialize_sync()
        if self.config.shutdown is False and len(self.symbols) > 0:
            asyncio.run(self.monitor_all_signals())

    async def shutdown(self):
        """Gracefully shutdown the signal bot."""
        logger.info("Shutting down signal bot")
        self.stop_monitoring()
        self.config.shutdown = True
        await self.mt5.shutdown()
        logger.info("Signal bot shutdown complete")

    def shutdown_sync(self):
        """Gracefully shutdown the signal bot synchronously."""
        logger.info("Shutting down signal bot")
        self.stop_monitoring()
        self.config.shutdown = True
        self.mt5.shutdown_sync()
        logger.info("Signal bot shutdown complete")