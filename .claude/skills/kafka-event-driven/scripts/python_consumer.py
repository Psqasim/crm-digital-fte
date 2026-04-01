"""
Simple Kafka Consumer (Python)

Demonstrates basic consumer with confluent-kafka-python library.

Install: pip install confluent-kafka

Usage: python python_consumer.py
"""

from confluent_kafka import Consumer, KafkaError
import sys


def main():
    # Consumer configuration
    conf = {
        'bootstrap.servers': 'localhost:9092',
        'group.id': 'python-consumer-group',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False,
        'max.poll.interval.ms': 300000
    }

    consumer = Consumer(conf)
    consumer.subscribe(['my-topic'])

    try:
        while True:
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition
                    continue
                else:
                    print(f'Error: {msg.error()}', file=sys.stderr)
                    break

            # Process message
            print(f'Consumed: key={msg.key().decode("utf-8") if msg.key() else None}, '
                  f'value={msg.value().decode("utf-8")}, '
                  f'partition={msg.partition()}, offset={msg.offset()}')

            # Manual commit
            consumer.commit(asynchronous=False)

    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()


if __name__ == '__main__':
    main()
