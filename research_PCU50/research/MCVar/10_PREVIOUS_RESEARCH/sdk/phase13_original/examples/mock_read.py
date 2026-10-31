from datetime import datetime, timezone

from mcvar_sdk import AcquisitionClient, Freshness, MockAdapter, Quality, RetryPolicy, SubscriptionRegistry


def main():
    # DEMO ONLY. This mock is not Siemens MCVar support and does not access a PCU.
    adapter = MockAdapter({"$DEMO.TEMPERATURE": 21.5, "$DEMO.MODE": "ready"})
    client = AcquisitionClient(adapter, retry_policy=RetryPolicy(attempts=2, delay=0.1))
    result = client.read(["$DEMO.TEMPERATURE", "$DEMO.MODE", "$DEMO.MISSING"])
    for observation in result.items:
        print(observation.address, observation.value, observation.quality.value, observation.freshness.value)

    registry = SubscriptionRegistry(client)
    token = registry.subscribe(["$DEMO.TEMPERATURE"], lambda update: print("poll", update.items[0].value), interval=2)
    try:
        input("Polling demo active. Press Enter to stop.\n")
    except EOFError:
        pass
    finally:
        registry.unsubscribe(token)
        registry.close()
        client.close()


if __name__ == "__main__":
    main()
