# Kafka Streams Guide

Complete guide for building real-time stream processing applications with Kafka Streams API.

## Table of Contents

1. [Overview](#overview)
2. [Core Concepts](#core-concepts)
3. [Topology Building](#topology-building)
4. [Stateless Transformations](#stateless-transformations)
5. [Stateful Operations](#stateful-operations)
6. [Windowing](#windowing)
7. [Joins](#joins)
8. [State Stores](#state-stores)
9. [Error Handling](#error-handling)
10. [Testing](#testing)

## Overview

Kafka Streams is a client library for building real-time streaming applications and microservices. It combines simplicity of standard Java application development with cluster technology benefits.

**Key features:**
- Exactly-once processing semantics
- No external dependencies (runs as part of your application)
- Stateful processing with fault-tolerant state stores
- Event-time and windowing semantics
- Interactive queries for state stores

## Core Concepts

### Streams and Tables

**KStream** - Unbounded stream of records (insert-only)
- Represents a partitioned event stream
- Each record is an independent event
- Example: Click events, sensor readings

**KTable** - Changelog stream (updates)
- Represents a partitioned table (latest value per key)
- Each record updates the previous value for the key
- Example: User profiles, product inventory

**GlobalKTable** - Fully replicated table
- All partitions available on every application instance
- Use for small lookup tables and enrichment

### Processor Topology

A topology is a DAG (directed acyclic graph) of stream processors:
- **Source processors** - Read from Kafka topics
- **Stream processors** - Transform data
- **Sink processors** - Write to Kafka topics

## Topology Building

### Basic Example

```java
Properties props = new Properties();
props.put(StreamsConfig.APPLICATION_ID_CONFIG, "streams-app");
props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:9092");
props.put(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.String().getClass());
props.put(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG, Serdes.String().getClass());

StreamsBuilder builder = new StreamsBuilder();

// Define topology
KStream<String, String> source = builder.stream("input-topic");
source.filter((key, value) -> value.length() > 5)
      .to("output-topic");

KafkaStreams streams = new KafkaStreams(builder.build(), props);
streams.start();
```

### Configuration Best Practices

```java
// Production configuration
props.put(StreamsConfig.PROCESSING_GUARANTEE_CONFIG, "exactly_once_v2");
props.put(StreamsConfig.REPLICATION_FACTOR_CONFIG, 3);
props.put(StreamsConfig.topicPrefix(TopicConfig.MIN_IN_SYNC_REPLICAS_CONFIG), 2);
props.put(StreamsConfig.NUM_STANDBY_REPLICAS_CONFIG, 1);
props.put(StreamsConfig.COMMIT_INTERVAL_MS_CONFIG, 1000);
props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
```

## Stateless Transformations

### Filter

```java
KStream<String, String> filtered = stream.filter((key, value) ->
    value != null && value.length() > 0);
```

### Map

```java
// Transform key and value
KStream<String, Integer> mapped = stream.map((key, value) ->
    KeyValue.pair(key.toUpperCase(), value.length()));

// Transform only value
KStream<String, Integer> mapValues = stream.mapValues(value ->
    value.length());
```

### FlatMap

```java
KStream<String, String> words = stream.flatMapValues(value ->
    Arrays.asList(value.toLowerCase().split("\\W+")));
```

### Branch

```java
Map<String, KStream<String, String>> branches = stream.split()
    .branch((key, value) -> value.startsWith("A"), Branched.as("a-branch"))
    .branch((key, value) -> value.startsWith("B"), Branched.as("b-branch"))
    .defaultBranch(Branched.as("default"));

KStream<String, String> aBranch = branches.get("a-branch");
```

### Merge

```java
KStream<String, String> merged = stream1.merge(stream2);
```

## Stateful Operations

### GroupBy and Aggregate

```java
KTable<String, Long> aggregated = stream
    .groupByKey()
    .aggregate(
        () -> 0L,  // Initializer
        (key, value, aggregate) -> aggregate + value.length(),  // Aggregator
        Materialized.<String, Long, KeyValueStore<Bytes, byte[]>>as("aggregated-store")
            .withKeySerde(Serdes.String())
            .withValueSerde(Serdes.Long())
    );
```

### Count

```java
KTable<String, Long> counts = stream
    .groupByKey()
    .count(Materialized.as("counts-store"));
```

### Reduce

```java
KTable<String, String> reduced = stream
    .groupByKey()
    .reduce((value1, value2) -> value1 + "," + value2);
```

## Windowing

### Tumbling Windows

Non-overlapping, fixed-size time intervals.

```java
Duration windowSize = Duration.ofMinutes(5);

KTable<Windowed<String>, Long> windowedCounts = stream
    .groupByKey()
    .windowedBy(TimeWindows.ofSizeWithNoGrace(windowSize))
    .count();

// Extract window boundaries
windowedCounts.toStream().foreach((windowedKey, count) -> {
    String key = windowedKey.key();
    Window window = windowedKey.window();
    Instant start = window.startTime();
    Instant end = window.endTime();
    System.out.printf("Key: %s, Window: %s-%s, Count: %d%n",
        key, start, end, count);
});
```

### Hopping Windows

Overlapping, fixed-size windows.

```java
Duration windowSize = Duration.ofMinutes(5);
Duration advanceSize = Duration.ofMinutes(1);

KTable<Windowed<String>, Long> windowedCounts = stream
    .groupByKey()
    .windowedBy(TimeWindows.ofSizeAndGrace(windowSize, Duration.ofSeconds(30))
        .advanceBy(advanceSize))
    .count();
```

### Sliding Windows

Windows defined by time difference between records.

```java
Duration timeDifference = Duration.ofMinutes(10);

KTable<Windowed<String>, Long> slidingCounts = stream
    .groupByKey()
    .windowedBy(SlidingWindows.ofTimeDifferenceWithNoGrace(timeDifference))
    .count();
```

### Session Windows

Dynamically sized windows based on activity.

```java
Duration inactivityGap = Duration.ofMinutes(5);

KTable<Windowed<String>, Long> sessionCounts = stream
    .groupByKey()
    .windowedBy(SessionWindows.ofInactivityGapWithNoGrace(inactivityGap))
    .count();
```

## Joins

### Stream-Stream Join

```java
// Inner join with 5-minute time window
KStream<String, String> joined = leftStream.join(
    rightStream,
    (leftValue, rightValue) -> leftValue + " + " + rightValue,
    JoinWindows.ofTimeDifferenceWithNoGrace(Duration.ofMinutes(5)),
    StreamJoined.with(Serdes.String(), Serdes.String(), Serdes.String())
);

// Left join
KStream<String, String> leftJoined = leftStream.leftJoin(
    rightStream,
    (leftValue, rightValue) -> leftValue + " + " +
        (rightValue == null ? "null" : rightValue),
    JoinWindows.ofTimeDifferenceWithNoGrace(Duration.ofMinutes(5))
);

// Outer join
KStream<String, String> outerJoined = leftStream.outerJoin(
    rightStream,
    (leftValue, rightValue) ->
        (leftValue == null ? "null" : leftValue) + " + " +
        (rightValue == null ? "null" : rightValue),
    JoinWindows.ofTimeDifferenceWithNoGrace(Duration.ofMinutes(5))
);
```

### Stream-Table Join

```java
// Enrich stream with table data
KStream<String, String> enriched = stream.join(
    table,
    (streamValue, tableValue) -> streamValue + " enriched with " + tableValue
);

// Left join (stream record emitted even if no table match)
KStream<String, String> leftJoined = stream.leftJoin(
    table,
    (streamValue, tableValue) -> streamValue + " + " +
        (tableValue == null ? "no-match" : tableValue)
);
```

### Table-Table Join

```java
// Inner join
KTable<String, String> joined = table1.join(
    table2,
    (value1, value2) -> value1 + " + " + value2
);

// Left join
KTable<String, String> leftJoined = table1.leftJoin(
    table2,
    (value1, value2) -> value1 + " + " +
        (value2 == null ? "null" : value2)
);

// Outer join
KTable<String, String> outerJoined = table1.outerJoin(
    table2,
    (value1, value2) ->
        (value1 == null ? "null" : value1) + " + " +
        (value2 == null ? "null" : value2)
);
```

### Stream-GlobalTable Join

```java
// No repartitioning needed - GlobalTable is fully replicated
KStream<String, String> enriched = stream.join(
    globalTable,
    (streamKey, streamValue) -> streamValue.substring(0, 3), // Key extractor
    (streamValue, globalTableValue) -> streamValue + " + " + globalTableValue
);
```

## State Stores

### Key-Value Store

```java
// Create store
StoreBuilder<KeyValueStore<String, Long>> storeBuilder =
    Stores.keyValueStoreBuilder(
        Stores.persistentKeyValueStore("my-store"),
        Serdes.String(),
        Serdes.Long()
    );

builder.addStateStore(storeBuilder);

// Access in processor
context.getStateStore("my-store");
```

### Window Store

```java
StoreBuilder<WindowStore<String, Long>> windowStoreBuilder =
    Stores.windowStoreBuilder(
        Stores.persistentWindowStore(
            "window-store",
            Duration.ofDays(1),
            Duration.ofMinutes(5),
            false
        ),
        Serdes.String(),
        Serdes.Long()
    );
```

### Interactive Queries

```java
// Query local state store
ReadOnlyKeyValueStore<String, Long> store = streams.store(
    StoreQueryParameters.fromNameAndType(
        "my-store",
        QueryableStoreTypes.keyValueStore()
    )
);

Long value = store.get("key");

// Range query
KeyValueIterator<String, Long> range = store.range("A", "Z");
while (range.hasNext()) {
    KeyValue<String, Long> entry = range.next();
    System.out.println(entry.key + " -> " + entry.value);
}
range.close();
```

## Error Handling

### Deserialization Error Handler

```java
props.put(StreamsConfig.DEFAULT_DESERIALIZATION_EXCEPTION_HANDLER_CLASS_CONFIG,
    LogAndContinueExceptionHandler.class);

// Or custom handler
public class CustomDeserializationExceptionHandler
    implements DeserializationExceptionHandler {

    @Override
    public DeserializationHandlerResponse handle(
        ProcessorContext context,
        ConsumerRecord<byte[], byte[]> record,
        Exception exception) {

        // Log to DLQ topic
        sendToDeadLetterQueue(record, exception);

        return DeserializationHandlerResponse.CONTINUE;
    }
}
```

### Production Error Handler

```java
props.put(StreamsConfig.DEFAULT_PRODUCTION_EXCEPTION_HANDLER_CLASS_CONFIG,
    DefaultProductionExceptionHandler.class);
```

### Uncaught Exception Handler

```java
streams.setUncaughtExceptionHandler((thread, throwable) -> {
    logger.error("Uncaught exception in thread {}", thread.getName(), throwable);

    // Decide whether to replace thread or shutdown
    if (isFatal(throwable)) {
        return StreamsUncaughtExceptionHandler.StreamThreadExceptionResponse.SHUTDOWN_APPLICATION;
    }
    return StreamsUncaughtExceptionHandler.StreamThreadExceptionResponse.REPLACE_THREAD;
});
```

## Testing

### Topology Test Driver

```java
@Test
public void testWordCount() {
    // Create test driver
    TopologyTestDriver testDriver = new TopologyTestDriver(
        topology,
        props
    );

    // Create test input topic
    TestInputTopic<String, String> inputTopic = testDriver.createInputTopic(
        "input-topic",
        new StringSerializer(),
        new StringSerializer()
    );

    // Create test output topic
    TestOutputTopic<String, Long> outputTopic = testDriver.createOutputTopic(
        "output-topic",
        new StringDeserializer(),
        new LongDeserializer()
    );

    // Pipe input
    inputTopic.pipeInput("key1", "hello world hello");

    // Verify output
    KeyValue<String, Long> output1 = outputTopic.readKeyValue();
    assertEquals("hello", output1.key);
    assertEquals(2L, output1.value);

    KeyValue<String, Long> output2 = outputTopic.readKeyValue();
    assertEquals("world", output2.key);
    assertEquals(1L, output2.value);

    testDriver.close();
}
```

### Testing with State Stores

```java
@Test
public void testStateStore() {
    TopologyTestDriver testDriver = new TopologyTestDriver(topology, props);

    // Access state store
    KeyValueStore<String, Long> store = testDriver.getKeyValueStore("my-store");

    // Verify state
    assertEquals(10L, store.get("key1"));

    testDriver.close();
}
```

## Performance Optimization

### Tuning Parameters

```java
// Cache size (reduces downstream updates)
props.put(StreamsConfig.CACHE_MAX_BYTES_BUFFERING_CONFIG, 10 * 1024 * 1024); // 10MB

// Commit interval
props.put(StreamsConfig.COMMIT_INTERVAL_MS_CONFIG, 1000); // 1 second

// Number of threads
props.put(StreamsConfig.NUM_STREAM_THREADS_CONFIG, 4);

// Buffering
props.put(StreamsConfig.BUFFERED_RECORDS_PER_PARTITION_CONFIG, 1000);
```

### Suppression

```java
// Suppress intermediate updates in windowed aggregation
KTable<Windowed<String>, Long> suppressed = windowedCounts.suppress(
    Suppressed.untilWindowCloses(Suppressed.BufferConfig.unbounded())
);
```

## Best Practices

1. **Use exactly-once semantics** for critical applications
2. **Configure standby replicas** for faster recovery
3. **Set appropriate retention** for changelog topics
4. **Use GlobalKTable** sparingly (fully replicated)
5. **Monitor lag metrics** for each topology
6. **Test topologies** with TopologyTestDriver
7. **Handle poison pills** with deserialization exception handlers
8. **Size state stores** appropriately (RocksDB tuning)
