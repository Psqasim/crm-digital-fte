# Schema Management Guide

Data contracts, schema evolution, and Schema Registry integration.

## Why Schema Management?

**Benefits:**
- **Data quality** - Prevent malformed data from entering Kafka
- **Documentation** - Schemas serve as API contracts
- **Evolution** - Change schemas safely over time
- **Compatibility** - Ensure producers and consumers remain compatible

## Schema Registry

Confluent Schema Registry provides centralized schema management for Kafka.

### Setup

**Docker:**

```bash
docker run -d \
  --name schema-registry \
  -p 8081:8081 \
  -e SCHEMA_REGISTRY_HOST_NAME=schema-registry \
  -e SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS=kafka:9092 \
  confluentinc/cp-schema-registry:latest
```

### REST API

**Register schema:**

```bash
curl -X POST http://localhost:8081/subjects/users-value/versions \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{
    "schema": "{\"type\":\"record\",\"name\":\"User\",\"fields\":[{\"name\":\"id\",\"type\":\"int\"},{\"name\":\"name\",\"type\":\"string\"}]}"
  }'
```

**Get latest schema:**

```bash
curl http://localhost:8081/subjects/users-value/versions/latest
```

**List all subjects:**

```bash
curl http://localhost:8081/subjects
```

## Avro Serialization

### Avro Schema

```json
{
  "type": "record",
  "name": "User",
  "namespace": "com.example",
  "fields": [
    {"name": "id", "type": "int"},
    {"name": "name", "type": "string"},
    {"name": "email", "type": ["null", "string"], "default": null},
    {"name": "created_at", "type": "long", "logicalType": "timestamp-millis"}
  ]
}
```

### Producer with Avro

```java
import io.confluent.kafka.serializers.KafkaAvroSerializer;
import org.apache.avro.Schema;
import org.apache.avro.generic.GenericData;
import org.apache.avro.generic.GenericRecord;

Properties props = new Properties();
props.put("bootstrap.servers", "localhost:9092");
props.put("key.serializer", StringSerializer.class.getName());
props.put("value.serializer", KafkaAvroSerializer.class.getName());
props.put("schema.registry.url", "http://localhost:8081");

// Define schema
String schemaString = "{\"type\":\"record\"," +
    "\"name\":\"User\"," +
    "\"fields\":[" +
    "{\"name\":\"id\",\"type\":\"int\"}," +
    "{\"name\":\"name\",\"type\":\"string\"}" +
    "]}";

Schema schema = new Schema.Parser().parse(schemaString);

// Create record
GenericRecord user = new GenericData.Record(schema);
user.put("id", 1);
user.put("name", "Alice");

// Send
KafkaProducer<String, GenericRecord> producer = new KafkaProducer<>(props);
producer.send(new ProducerRecord<>("users", "user-1", user));
producer.close();
```

### Consumer with Avro

```java
import io.confluent.kafka.serializers.KafkaAvroDeserializer;
import org.apache.avro.generic.GenericRecord;

Properties props = new Properties();
props.put("bootstrap.servers", "localhost:9092");
props.put("group.id", "avro-consumer-group");
props.put("key.deserializer", StringDeserializer.class.getName());
props.put("value.deserializer", KafkaAvroDeserializer.class.getName());
props.put("schema.registry.url", "http://localhost:8081");
props.put("specific.avro.reader", "false");

KafkaConsumer<String, GenericRecord> consumer = new KafkaConsumer<>(props);
consumer.subscribe(Collections.singletonList("users"));

while (true) {
    ConsumerRecords<String, GenericRecord> records = consumer.poll(Duration.ofMillis(100));
    for (ConsumerRecord<String, GenericRecord> record : records) {
        GenericRecord user = record.value();
        System.out.printf("User: id=%d, name=%s%n",
            user.get("id"), user.get("name"));
    }
}
```

### Specific Avro (Code Generation)

```bash
# Generate Java classes from Avro schema
java -jar avro-tools.jar compile schema user.avsc output/
```

```java
// Use generated class
import com.example.User;

Properties props = new Properties();
props.put("schema.registry.url", "http://localhost:8081");
props.put("specific.avro.reader", "true");

User user = User.newBuilder()
    .setId(1)
    .setName("Alice")
    .setEmail("alice@example.com")
    .setCreatedAt(System.currentTimeMillis())
    .build();

producer.send(new ProducerRecord<>("users", user));
```

## JSON Schema

### JSON Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "User",
  "type": "object",
  "properties": {
    "id": {"type": "integer"},
    "name": {"type": "string"},
    "email": {"type": "string", "format": "email"},
    "created_at": {"type": "string", "format": "date-time"}
  },
  "required": ["id", "name"]
}
```

### Producer with JSON Schema

```java
import io.confluent.kafka.serializers.json.KafkaJsonSchemaSerializer;

Properties props = new Properties();
props.put("value.serializer", KafkaJsonSchemaSerializer.class.getName());
props.put("schema.registry.url", "http://localhost:8081");

Map<String, Object> user = new HashMap<>();
user.put("id", 1);
user.put("name", "Alice");
user.put("email", "alice@example.com");

producer.send(new ProducerRecord<>("users", user));
```

## Protobuf

### Protobuf Schema

```protobuf
syntax = "proto3";

package com.example;

message User {
  int32 id = 1;
  string name = 2;
  string email = 3;
  int64 created_at = 4;
}
```

### Producer with Protobuf

```java
import io.confluent.kafka.serializers.protobuf.KafkaProtobufSerializer;

Properties props = new Properties();
props.put("value.serializer", KafkaProtobufSerializer.class.getName());
props.put("schema.registry.url", "http://localhost:8081");

User user = User.newBuilder()
    .setId(1)
    .setName("Alice")
    .setEmail("alice@example.com")
    .setCreatedAt(System.currentTimeMillis())
    .build();

producer.send(new ProducerRecord<>("users", user));
```

## Schema Evolution

### Compatibility Modes

**BACKWARD (default):**
- New schema can read old data
- Safe to add optional fields with defaults
- Safe to delete fields

**FORWARD:**
- Old schema can read new data
- Safe to add new fields
- Safe to delete optional fields

**FULL:**
- Both BACKWARD and FORWARD
- Only add/remove optional fields with defaults

**NONE:**
- No compatibility checks

### Set Compatibility Mode

```bash
# Global default
curl -X PUT http://localhost:8081/config \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"compatibility": "BACKWARD"}'

# Per subject
curl -X PUT http://localhost:8081/config/users-value \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"compatibility": "FULL"}'
```

### Schema Evolution Examples

**BACKWARD compatible - Add optional field:**

```json
// V1
{
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "id", "type": "int"},
    {"name": "name", "type": "string"}
  ]
}

// V2 (BACKWARD compatible)
{
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "id", "type": "int"},
    {"name": "name", "type": "string"},
    {"name": "email", "type": ["null", "string"], "default": null}
  ]
}
```

**NOT BACKWARD compatible - Remove required field:**

```json
// V2 (breaks BACKWARD compatibility)
{
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "id", "type": "int"}
    // Removed "name" field
  ]
}
```

**FORWARD compatible - Add new field:**

```json
// V2 (FORWARD compatible)
{
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "id", "type": "int"},
    {"name": "name", "type": "string"},
    {"name": "age", "type": "int", "default": 0}
  ]
}
```

## Subject Naming Strategies

### TopicNameStrategy (default)

Subject name: `<topic>-key` or `<topic>-value`

```java
props.put("value.subject.name.strategy",
    "io.confluent.kafka.serializers.subject.TopicNameStrategy");
```

### RecordNameStrategy

Subject name: `<record-name>`

```java
props.put("value.subject.name.strategy",
    "io.confluent.kafka.serializers.subject.RecordNameStrategy");
```

### TopicRecordNameStrategy

Subject name: `<topic>-<record-name>`

```java
props.put("value.subject.name.strategy",
    "io.confluent.kafka.serializers.subject.TopicRecordNameStrategy");
```

## Schema Registry Security

### Enable authentication

**schema-registry.properties:**

```properties
# Basic auth
authentication.method=BASIC
authentication.realm=SchemaRegistry
authentication.roles=admin,developer

# HTTPS
listeners=https://0.0.0.0:8081
ssl.keystore.location=/path/to/keystore.jks
ssl.keystore.password=password
ssl.key.password=password
```

### Client configuration

```java
props.put("schema.registry.url", "https://localhost:8081");
props.put("basic.auth.credentials.source", "USER_INFO");
props.put("basic.auth.user.info", "username:password");
```

## Best Practices

1. **Use Schema Registry** for production systems
2. **Choose appropriate compatibility mode** for your use case
3. **Version schemas** systematically (v1, v2, etc.)
4. **Document schema changes** in commit messages
5. **Test schema changes** before deploying
6. **Use specific Avro readers** for better performance
7. **Set reasonable subject naming strategy**
8. **Monitor schema registry** health and performance
9. **Backup schema registry data** regularly
10. **Use logical types** for dates, decimals, etc.

## Comparison: Avro vs JSON Schema vs Protobuf

| Feature | Avro | JSON Schema | Protobuf |
|---------|------|-------------|----------|
| Schema evolution | Excellent | Good | Excellent |
| Serialization size | Small | Large | Small |
| Performance | Fast | Slower | Fastest |
| Human readable | Binary | Text | Binary |
| Dynamic typing | Yes | Yes | No |
| Ecosystem | Kafka native | Web-friendly | Google |
| Best for | Kafka pipelines | APIs | gRPC services |
