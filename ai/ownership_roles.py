"""Keep source role types distinct; association is never assumed to be control."""
def classify(role):
 text=(role or '').lower()
 if 'ownership interest' in text or ('partnership' in text and 'interest' in text):return 'REPORTED_OWNERSHIP_INTEREST'
 if 'operational/managerial control' in text:return 'REPORTED_CONTROL_ROLE'
 return 'REPORTED_ASSOCIATION_ROLE'
