import asyncio
import src.crypto
import sys

def main():
    if len(sys.argv) != 2:
        if len(sys.argv) < 2:
            print('Error: Not enough arguments provided. Please provide a search term.')
            return
        else:
            print('Error: Too many arguments provided.')
            return

    query_string = sys.argv[1]
    asyncio.run(src.crypto.search(query_string))

if __name__ == '__main__':
    sys.exit(main())