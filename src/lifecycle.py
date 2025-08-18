"""
Lifecycle Manager

A background service that continuously runs the lifecycle_manager to process
seed growth, animal maturation, and product harvesting in the farm simulation.
"""

import time
import signal
import sys
import logging
from datetime import datetime
from typing import Optional
from farm import lifecycle_manager

# Configuration
DEFAULT_CYCLE_INTERVAL = 60  # seconds between lifecycle cycles
DEFAULT_LOG_LEVEL = logging.INFO

class LifecycleManager:
    """
    A daemon service that runs the farm lifecycle manager continuously.
    """
    
    def __init__(self, cycle_interval: int = DEFAULT_CYCLE_INTERVAL, log_level: int = DEFAULT_LOG_LEVEL):
        self.cycle_interval = cycle_interval
        self.running = False
        self.cycle_count = 0
        
        # Setup logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('lifecycle_manager.log')
            ]
        )
        self.logger = logging.getLogger('LifecycleManager')
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum: int, frame: Optional[object]) -> None:
        """Handle shutdown signals gracefully."""
        signal_names = {signal.SIGINT: 'SIGINT', signal.SIGTERM: 'SIGTERM'}
        signal_name = signal_names.get(signum, f'Signal {signum}')
        self.logger.info(f"Received {signal_name}, shutting down gracefully...")
        self.stop()
    
    def start(self) -> None:
        """Start the daemon and begin the lifecycle management loop."""
        self.logger.info("🌱 Farm Lifecycle Daemon starting...")
        self.logger.info(f"Cycle interval: {self.cycle_interval} seconds")
        self.running = True
        
        try:
            self._run_lifecycle_loop()
        except Exception as e:
            self.logger.error(f"Fatal error in daemon: {e}")
            raise
        finally:
            self.logger.info("🌾 Farm Lifecycle Daemon stopped.")
    
    def stop(self) -> None:
        """Stop the daemon."""
        self.running = False
    
    def _run_lifecycle_loop(self) -> None:
        """Main loop that runs the lifecycle manager continuously."""
        while self.running:
            cycle_start = time.time()
            self.cycle_count += 1
            
            self.logger.info(f"🔄 Starting lifecycle cycle #{self.cycle_count}")
            
            try:
                # Run the lifecycle manager
                lifecycle_manager()
                self.logger.info(f"✅ Lifecycle cycle #{self.cycle_count} completed successfully")
                
            except Exception as e:
                self.logger.error(f"❌ Error in lifecycle cycle #{self.cycle_count}: {e}")
            
            # Calculate sleep time to maintain consistent intervals
            cycle_duration = time.time() - cycle_start
            sleep_time = max(0, self.cycle_interval - cycle_duration)
            
            if sleep_time > 0:
                self.logger.debug(f"⏰ Sleeping for {sleep_time:.1f} seconds until next cycle")
                time.sleep(sleep_time)
            else:
                self.logger.warning(f"⚠️  Lifecycle cycle took {cycle_duration:.1f}s, longer than interval of {self.cycle_interval}s")

def main() -> None:
    """Main entry point for the lifecycle manager."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Lifecycle Manager")
    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=DEFAULT_CYCLE_INTERVAL,
        help=f'Interval between lifecycle cycles in seconds (default: {DEFAULT_CYCLE_INTERVAL})'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Enable quiet mode (errors only)'
    )
    
    args = parser.parse_args()
    
    # Determine log level
    log_level = DEFAULT_LOG_LEVEL
    if args.verbose:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.ERROR
    
    # Create and start the daemon
    daemon = LifecycleManager(cycle_interval=args.interval, log_level=log_level)
    
    try:
        daemon.start()
    except KeyboardInterrupt:
        print("\nDaemon interrupted by user")
    except Exception as e:
        print(f"Daemon failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
