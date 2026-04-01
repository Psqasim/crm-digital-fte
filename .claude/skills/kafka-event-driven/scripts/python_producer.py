"""
Simple Kafka Producer (Python)

Demonstrates basic producer with confluent-kafka-python library.

Install: pip install confluent-kafka

Usage: python python_producer.py
"""

from confluent_kafka import Producer
import sys


def delivery_callback(err, msg):
    """Callback for message delivery reports"""
    if err is not None:
        print(f'Message delivery failed: {err}', file=sys.stderr)
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}')


def main():
    # Producer configuration
    conf = {
        'bootstrap.servers': 'localhost:9092',
        'client.id': 'python-producer',
        'acks': 'all',
        'retries': 3,
        'enable.idempotence': True,
        'compression.type': 'lz4'
    }

    producer = Producer(conf)

    topic = 'my-topic'

    try:
        # Send 10 messages
        for i in range(10):
            key = f'key-{i}'
            value = f'value-{i}'

            # Async produce with callback
            producer.produce(
                topic,
                key=key.encode('utf-8'),
                value=value.encode('utf-8'),
                callback=delivery_callback
            )

            # Trigger callbacks
            producer.poll(0)

        # Wait for all messages to be delivered
        producer.flush()

    except KeyboardInterrupt:
        pass
    finally:
        producer.flush()
        print(f'{producer} flushed')


if __name__ == '__main__':
    main()
