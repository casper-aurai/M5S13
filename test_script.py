
import argparse
import sys

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    
    p = argparse.ArgumentParser()
    p.add_argument("html")
    p.add_argument("--encoding", default="utf-8")
    
    args = p.parse_args(argv)
    print("Parsed successfully")
    print("args.encoding:", args.encoding)
    return 0

if __name__ == "__main__":
    sys.exit(main())
