from dhanhq import marketfeed

# Add your Dhan Client ID and Access Token
client_id = '1100467218'
access_token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzY2ODI2NTU1LCJpYXQiOjE3NjY3NDAxNTUsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAwNDY3MjE4In0.7RsCcJ2Q_J0kRXQTXjRv-6y2AFiycgOkcP4RKRXEIDZbafKYzRjdxEB8Bv-Rc4VEF9C8irpwJJWOSSUT-4213Q'

# Structure for subscribing is (exchange_segment, "security_id", subscription_type)

instruments = [(marketfeed.NSE, "1333", marketfeed.Ticker),   # Ticker - Ticker Data
    (marketfeed.NSE, "1333", marketfeed.Quote),     # Quote - Quote Data
    (marketfeed.NSE, "1333", marketfeed.Full),      # Full - Full Packet
    (marketfeed.NSE, "11915", marketfeed.Ticker),
    (marketfeed.NSE, "11915", marketfeed.Full)]

version = "v2"          # Mention Version and set to latest version 'v2'

# In case subscription_type is left as blank, by default Ticker mode will be subscribed.

try:
    data = marketfeed.DhanFeed(client_id, access_token, instruments, version)
    while True:
        data.run_forever()
        response = data.get_data()
        print(response)

except Exception as e:
    print(e)

