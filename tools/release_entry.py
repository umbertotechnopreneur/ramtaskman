"""Console entry point for the self-contained release bundle."""
import multiprocessing
import sys

if __name__ == '__main__':
    multiprocessing.freeze_support()
    if sys.argv[1:] == ['--verify-bundle']:
        import asyncio
        from bundle_smoke import verify
        asyncio.run(verify())
    else:
        from ramtaskman.cli import main
        raise SystemExit(main())
