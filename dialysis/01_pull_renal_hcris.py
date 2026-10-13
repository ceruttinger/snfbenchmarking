"""API-only policy guard for the renal cost-report scaffold.

No official raw renal cost-report API has been verified. Provider-directory and
quality APIs cannot replace CMS-265-11 financial data. Never fall back to ZIPs.
"""

def main():
    raise RuntimeError('No official raw renal cost-report API has been verified. Bulk downloads are disabled. Dialysis financial metrics remain unavailable pending a verified API source.')

if __name__ == '__main__':
    main()
