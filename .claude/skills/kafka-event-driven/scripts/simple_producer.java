/**
 * Simple Kafka Producer
 *
 * Demonstrates basic producer configuration and message sending with:
 * - Proper error handling
 * - Async callbacks
 * - Graceful shutdown
 *
 * Dependencies: kafka-clients
 */

import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.serialization.StringSerializer;
import java.util.Properties;

public class SimpleProducer {
    public static void main(String[] args) {
        // Producer configuration
        Properties props = new Properties();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:9092");
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());

        // Production-ready settings
        props.put(ProducerConfig.ACKS_CONFIG, "all");
        props.put(ProducerConfig.RETRIES_CONFIG, 3);
        props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);
        props.put(ProducerConfig.COMPRESSION_TYPE_CONFIG, "lz4");

        KafkaProducer<String, String> producer = new KafkaProducer<>(props);

        try {
            // Send 10 messages
            for (int i = 0; i < 10; i++) {
                String key = "key-" + i;
                String value = "value-" + i;

                ProducerRecord<String, String> record =
                    new ProducerRecord<>("my-topic", key, value);

                // Async send with callback
                producer.send(record, (metadata, exception) -> {
                    if (exception != null) {
                        System.err.println("Error sending message: " + exception.getMessage());
                    } else {
                        System.out.printf("Sent: %s -> partition=%d, offset=%d%n",
                            key, metadata.partition(), metadata.offset());
                    }
                });
            }
        } finally {
            producer.flush();
            producer.close();
        }
    }
}
