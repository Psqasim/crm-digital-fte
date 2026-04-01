# Kafka Connect Guide

Complete guide for building data pipelines with Kafka Connect for integrating Kafka with external systems.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Getting Started](#getting-started)
4. [Source Connectors](#source-connectors)
5. [Sink Connectors](#sink-connectors)
6. [REST API](#rest-api)
7. [Connector Configuration](#connector-configuration)
8. [Custom Connectors](#custom-connectors)
9. [Transforms](#transforms)
10. [Error Handling](#error-handling)
11. [Monitoring](#monitoring)

## Overview

Kafka Connect is a framework for connecting Kafka with external systems such as databases, key-value stores, search indexes, and file systems.

**Key features:**
- **Distributed and standalone modes** - Scale from development to production
- **REST API** - Easy management and monitoring
- **Automatic offset management** - Built-in fault tolerance
- **Streaming and batch integration** - Flexible data movement
- **Pluggable architecture** - Extensive connector ecosystem

## Architecture

###

 Components

- **Workers** - JVM processes that execute connectors and tasks
- **Connectors** - High-level abstraction for data movement
- **Tasks** - Actual units of work (parallelism)
- **Converters** - Serialization between Kafka and external systems
- **Transforms** - Lightweight message modification

### Modes

**Standalone mode** - Single process (development/testing)
```bash
bin/connect-standalone.sh config/connect-standalone.properties \
    config/source-connector.properties
```

**Distributed mode** - Scalable, fault-tolerant (production)
```bash
bin/connect-distributed.sh config/connect-distributed.properties
```

## Getting Started

### Configuration Files

**connect-distributed.properties:**

```properties
# Kafka broker connection
bootstrap.servers=localhost:9092

# Connect cluster identity
group.id=connect-cluster

# Topic for connector and task configuration
config.storage.topic=connect-configs
config.storage.replication.factor=3

# Topic for connector offsets
offset.storage.topic=connect-offsets
offset.storage.replication.factor=3

# Topic for connector status
status.storage.topic=connect-status
status.storage.replication.factor=3

# Converters
key.converter=org.apache.kafka.connect.json.JsonConverter
value.converter=org.apache.kafka.connect.json.JsonConverter
key.converter.schemas.enable=false
value.converter.schemas.enable=false

# REST API
rest.port=8083
rest.advertised.host.name=localhost

# Plugin path
plugin.path=/usr/local/share/kafka/plugins
```

### Start Distributed Cluster

```bash
# Start 3 workers for fault tolerance
bin/connect-distributed.sh config/connect-distributed.properties &
bin/connect-distributed.sh config/connect-distributed.properties &
bin/connect-distributed.sh config/connect-distributed.properties &
```

## Source Connectors

Source connectors read data from external systems and produce to Kafka topics.

### File Source Connector Example

```json
{
  "name": "file-source",
  "config": {
    "connector.class": "org.apache.kafka.connect.file.FileStreamSourceConnector",
    "tasks.max": "1",
    "file": "/tmp/input.txt",
    "topic": "file-input-topic"
  }
}
```

**Deploy via REST API:**

```bash
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @file-source.json
```

### JDBC Source Connector

```json
{
  "name": "postgres-source",
  "config": {
    "connector.class": "io.confluent.connect.jdbc.JdbcSourceConnector",
    "tasks.max": "1",
    "connection.url": "jdbc:postgresql://localhost:5432/mydb",
    "connection.user": "postgres",
    "connection.password": "password",
    "mode": "incrementing",
    "incrementing.column.name": "id",
    "topic.prefix": "postgres-",
    "poll.interval.ms": "1000"
  }
}
```

**Modes:**
- `incrementing` - Track by auto-incrementing column
- `timestamp` - Track by timestamp column
- `timestamp+incrementing` - Combination of both
- `bulk` - Full table snapshot (no tracking)

### Debezium CDC Source Connector

```json
{
  "name": "postgres-cdc",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "localhost",
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "password",
    "database.dbname": "mydb",
    "database.server.name": "postgres-cdc",
    "table.include.list": "public.users,public.orders",
    "plugin.name": "pgoutput"
  }
}
```

## Sink Connectors

Sink connectors read from Kafka topics and write to external systems.

### File Sink Connector

```json
{
  "name": "file-sink",
  "config": {
    "connector.class": "org.apache.kafka.connect.file.FileStreamSinkConnector",
    "tasks.max": "1",
    "file": "/tmp/output.txt",
    "topics": "file-input-topic"
  }
}
```

### JDBC Sink Connector

```json
{
  "name": "postgres-sink",
  "config": {
    "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
    "tasks.max": "3",
    "connection.url": "jdbc:postgresql://localhost:5432/mydb",
    "connection.user": "postgres",
    "connection.password": "password",
    "topics": "orders",
    "auto.create": "true",
    "auto.evolve": "true",
    "insert.mode": "upsert",
    "pk.mode": "record_key",
    "pk.fields": "order_id"
  }
}
```

### Elasticsearch Sink Connector

```json
{
  "name": "elasticsearch-sink",
  "config": {
    "connector.class": "io.confluent.connect.elasticsearch.ElasticsearchSinkConnector",
    "tasks.max": "2",
    "topics": "logs",
    "connection.url": "http://localhost:9200",
    "type.name": "_doc",
    "key.ignore": "false",
    "schema.ignore": "true"
  }
}
```

## REST API

### List Connectors

```bash
curl http://localhost:8083/connectors
```

### Create Connector

```bash
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-connector",
    "config": {
      "connector.class": "...",
      "tasks.max": "1"
    }
  }'
```

### Get Connector Status

```bash
curl http://localhost:8083/connectors/my-connector/status
```

### Get Connector Configuration

```bash
curl http://localhost:8083/connectors/my-connector/config
```

### Update Connector Configuration

```bash
curl -X PUT http://localhost:8083/connectors/my-connector/config \
  -H "Content-Type: application/json" \
  -d '{
    "connector.class": "...",
    "tasks.max": "2"
  }'
```

### Pause Connector

```bash
curl -X PUT http://localhost:8083/connectors/my-connector/pause
```

### Resume Connector

```bash
curl -X PUT http://localhost:8083/connectors/my-connector/resume
```

### Restart Connector

```bash
curl -X POST http://localhost:8083/connectors/my-connector/restart
```

### Delete Connector

```bash
curl -X DELETE http://localhost:8083/connectors/my-connector
```

### List Connector Plugins

```bash
curl http://localhost:8083/connector-plugins
```

### Validate Connector Config

```bash
curl -X PUT http://localhost:8083/connector-plugins/JdbcSourceConnector/config/validate \
  -H "Content-Type: application/json" \
  -d '{
    "connector.class": "io.confluent.connect.jdbc.JdbcSourceConnector",
    "connection.url": "jdbc:postgresql://localhost:5432/mydb"
  }'
```

## Connector Configuration

### Common Configuration Parameters

```properties
# Connector class (required)
connector.class=io.confluent.connect.jdbc.JdbcSourceConnector

# Maximum tasks for parallelism (required)
tasks.max=3

# Connector name (set via REST API)
name=my-connector

# Error tolerance
errors.tolerance=none  # or 'all'
errors.log.enable=true
errors.log.include.messages=true

# Dead letter queue
errors.deadletterqueue.topic.name=dlq-topic
errors.deadletterqueue.topic.replication.factor=3
errors.deadletterqueue.context.headers.enable=true

# Retries
errors.retry.timeout=300000  # 5 minutes
errors.retry.delay.max.ms=60000  # 1 minute
```

### Converters

**JSON Converter:**

```properties
key.converter=org.apache.kafka.connect.json.JsonConverter
value.converter=org.apache.kafka.connect.json.JsonConverter
key.converter.schemas.enable=true
value.converter.schemas.enable=true
```

**Avro Converter (with Schema Registry):**

```properties
key.converter=io.confluent.connect.avro.AvroConverter
key.converter.schema.registry.url=http://localhost:8081
value.converter=io.confluent.connect.avro.AvroConverter
value.converter.schema.registry.url=http://localhost:8081
```

**String Converter:**

```properties
key.converter=org.apache.kafka.connect.storage.StringConverter
value.converter=org.apache.kafka.connect.storage.StringConverter
```

## Custom Connectors

### Source Connector Implementation

```java
public class CustomSourceConnector extends SourceConnector {

    private Map<String, String> configProps;

    @Override
    public void start(Map<String, String> props) {
        this.configProps = props;
    }

    @Override
    public Class<? extends Task> taskClass() {
        return CustomSourceTask.class;
    }

    @Override
    public List<Map<String, String>> taskConfigs(int maxTasks) {
        List<Map<String, String>> configs = new ArrayList<>();
        for (int i = 0; i < maxTasks; i++) {
            configs.add(configProps);
        }
        return configs;
    }

    @Override
    public void stop() {
        // Cleanup
    }

    @Override
    public ConfigDef config() {
        return new ConfigDef()
            .define("file", ConfigDef.Type.STRING,
                ConfigDef.Importance.HIGH, "Source file path")
            .define("topic", ConfigDef.Type.STRING,
                ConfigDef.Importance.HIGH, "Target topic");
    }

    @Override
    public String version() {
        return "1.0.0";
    }
}
```

### Source Task Implementation

```java
public class CustomSourceTask extends SourceTask {

    private String filename;
    private String topic;
    private BufferedReader reader;
    private Long position = 0L;

    @Override
    public void start(Map<String, String> props) {
        filename = props.get("file");
        topic = props.get("topic");

        // Recover offset
        Map<String, Object> offset = context.offsetStorageReader()
            .offset(Collections.singletonMap("filename", filename));

        if (offset != null) {
            position = (Long) offset.get("position");
        }

        // Open file and seek to position
        reader = new BufferedReader(new FileReader(filename));
        reader.skip(position);
    }

    @Override
    public List<SourceRecord> poll() throws InterruptedException {
        List<SourceRecord> records = new ArrayList<>();

        try {
            String line;
            while ((line = reader.readLine()) != null && records.size() < 100) {
                Map<String, Object> sourcePartition =
                    Collections.singletonMap("filename", filename);
                Map<String, Object> sourceOffset =
                    Collections.singletonMap("position", position);

                SourceRecord record = new SourceRecord(
                    sourcePartition,
                    sourceOffset,
                    topic,
                    Schema.STRING_SCHEMA,
                    line
                );

                records.add(record);
                position += line.length() + 1;
            }
        } catch (IOException e) {
            throw new ConnectException(e);
        }

        return records;
    }

    @Override
    public void stop() {
        try {
            if (reader != null) {
                reader.close();
            }
        } catch (IOException e) {
            // Ignore
        }
    }

    @Override
    public String version() {
        return "1.0.0";
    }
}
```

## Transforms

Single Message Transforms (SMTs) allow lightweight message modification.

### Insert Field

```json
{
  "transforms": "InsertTimestamp",
  "transforms.InsertTimestamp.type": "org.apache.kafka.connect.transforms.InsertField$Value",
  "transforms.InsertTimestamp.timestamp.field": "event_timestamp"
}
```

### Mask Field

```json
{
  "transforms": "MaskField",
  "transforms.MaskField.type": "org.apache.kafka.connect.transforms.MaskField$Value",
  "transforms.MaskField.fields": "ssn,credit_card",
  "transforms.MaskField.replacement": "****"
}
```

### Filter

```json
{
  "transforms": "FilterDeletes",
  "transforms.FilterDeletes.type": "io.confluent.connect.transforms.Filter",
  "transforms.FilterDeletes.filter.condition": "$[?(@.op == 'd')]",
  "transforms.FilterDeletes.filter.type": "exclude"
}
```

### Route to Different Topic

```json
{
  "transforms": "Route",
  "transforms.Route.type": "org.apache.kafka.connect.transforms.RegexRouter",
  "transforms.Route.regex": ".*",
  "transforms.Route.replacement": "my-prefix-$0"
}
```

### Flatten Nested Structure

```json
{
  "transforms": "Flatten",
  "transforms.Flatten.type": "org.apache.kafka.connect.transforms.Flatten$Value",
  "transforms.Flatten.delimiter": "_"
}
```

## Error Handling

### Dead Letter Queue

```json
{
  "config": {
    "errors.tolerance": "all",
    "errors.deadletterqueue.topic.name": "connect-dlq",
    "errors.deadletterqueue.topic.replication.factor": "3",
    "errors.deadletterqueue.context.headers.enable": "true"
  }
}
```

### Retry Configuration

```json
{
  "config": {
    "errors.retry.timeout": "300000",
    "errors.retry.delay.max.ms": "60000"
  }
}
```

## Monitoring

### Key Metrics

**Connector-level metrics:**
- `connector-total-task-count` - Number of tasks
- `connector-running-task-count` - Running tasks
- `connector-paused-task-count` - Paused tasks
- `connector-failed-task-count` - Failed tasks

**Source connector metrics:**
- `source-record-poll-rate` - Records polled per second
- `source-record-write-rate` - Records written to Kafka per second

**Sink connector metrics:**
- `sink-record-read-rate` - Records read from Kafka per second
- `sink-record-send-rate` - Records sent to sink per second
- `sink-record-lag-max` - Maximum lag across partitions

### Health Check

```bash
# Check worker health
curl http://localhost:8083/

# Check specific connector
curl http://localhost:8083/connectors/my-connector/status
```

## Best Practices

1. **Use distributed mode** in production for fault tolerance
2. **Set appropriate `tasks.max`** based on data volume and parallelism needs
3. **Enable error handling** with DLQ for production connectors
4. **Monitor connector lag** especially for sink connectors
5. **Use converters** that match your data format (Avro for structured data)
6. **Configure replication factor** for internal topics (3 recommended)
7. **Use transforms sparingly** - complex logic belongs in stream processing
8. **Version your connectors** for reproducibility
9. **Test connector configuration** with validate endpoint before deploying
10. **Set reasonable poll intervals** to balance latency and load
