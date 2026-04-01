# Kafka Operations Guide

Production deployment, monitoring, and operational best practices.

## Production Cluster Setup

### Hardware Recommendations

**Broker specifications:**
- CPU: 24+ cores
- RAM: 64GB+ (heap: 6-8GB, page cache: rest)
- Disk: SSDs for low latency, RAID 10
- Network: 10 Gbps+

### Cluster Sizing

**Formula:** `Brokers = (Replication Factor × Target Throughput) / Broker Throughput`

**Example:** For 100 MB/s throughput with RF=3: `(3 × 100) / 100 = 3 brokers minimum`

### Configuration

**server.properties (production):**

```properties
# Broker identity
broker.id=1
advertised.listeners=PLAINTEXT://kafka1.example.com:9092

# Zookeeper/KRaft
controller.quorum.voters=1@kafka1:9093,2@kafka2:9093,3@kafka3:9093

# Data directories (use multiple disks)
log.dirs=/data1/kafka-logs,/data2/kafka-logs,/data3/kafka-logs

# Replication
default.replication.factor=3
min.insync.replicas=2
unclean.leader.election.enable=false

# Log retention
log.retention.hours=168
log.retention.bytes=-1
log.segment.bytes=1073741824

# Performance
num.network.threads=8
num.io.threads=16
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600

# Compression
compression.type=producer

# JVM settings
KAFKA_HEAP_OPTS="-Xmx6g -Xms6g"
KAFKA_JVM_PERFORMANCE_OPTS="-XX:+UseG1GC -XX:MaxGCPauseMillis=20"
```

## Monitoring

### JMX Metrics

**Key broker metrics:**

```bash
# Under-replicated partitions (should be 0)
kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions

# Offline partitions (should be 0)
kafka.controller:type=KafkaController,name=OfflinePartitionsCount

# Active controller count (should be 1)
kafka.controller:type=KafkaController,name=ActiveControllerCount

# Request rate
kafka.network:type=RequestMetrics,name=RequestsPerSec,request={Produce|Fetch}

# Request latency
kafka.network:type=RequestMetrics,name=TotalTimeMs,request={Produce|Fetch}
```

**Producer metrics:**

```bash
# Send rate
kafka.producer:type=producer-metrics,client-id=*,name=record-send-rate

# Error rate
kafka.producer:type=producer-metrics,client-id=*,name=record-error-rate

# Batch size
kafka.producer:type=producer-metrics,client-id=*,name=batch-size-avg

# Request latency
kafka.producer:type=producer-metrics,client-id=*,name=request-latency-avg
```

**Consumer metrics:**

```bash
# Fetch rate
kafka.consumer:type=consumer-fetch-manager-metrics,client-id=*,name=records-consumed-rate

# Lag
kafka.consumer:type=consumer-fetch-manager-metrics,client-id=*,partition=*,topic=*,name=records-lag

# Commit latency
kafka.consumer:type=consumer-coordinator-metrics,client-id=*,name=commit-latency-avg
```

### Monitoring Stack

**Prometheus + Grafana setup:**

```yaml
# docker-compose.yml
services:
  kafka-exporter:
    image: danielqsj/kafka-exporter
    command:
      - --kafka.server=kafka1:9092
      - --kafka.server=kafka2:9092
      - --kafka.server=kafka3:9092
    ports:
      - "9308:9308"

  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
```

**prometheus.yml:**

```yaml
scrape_configs:
  - job_name: 'kafka'
    static_configs:
      - targets: ['kafka-exporter:9308']
```

### Alerting Rules

**Critical alerts:**

```yaml
groups:
  - name: kafka_alerts
    rules:
      - alert: UnderReplicatedPartitions
        expr: kafka_server_replicamanager_underreplicatedpartitions > 0
        for: 5m
        annotations:
          summary: "Under-replicated partitions detected"

      - alert: OfflinePartitions
        expr: kafka_controller_kafkacontroller_offlinepartitionscount > 0
        for: 1m
        annotations:
          summary: "Offline partitions detected"

      - alert: ConsumerLag
        expr: kafka_consumer_fetch_manager_records_lag > 10000
        for: 10m
        annotations:
          summary: "High consumer lag"
```

## Security

### SSL/TLS Configuration

**Generate certificates:**

```bash
# Create CA
openssl req -new -x509 -keyout ca-key -out ca-cert -days 365

# Create keystore
keytool -keystore kafka.server.keystore.jks -alias localhost \
  -validity 365 -genkey -keyalg RSA

# Sign certificate
keytool -keystore kafka.server.keystore.jks -alias localhost \
  -certreq -file cert-file

openssl x509 -req -CA ca-cert -CAkey ca-key -in cert-file \
  -out cert-signed -days 365 -CAcreateserial

# Import to keystore
keytool -keystore kafka.server.keystore.jks -alias CARoot \
  -import -file ca-cert

keytool -keystore kafka.server.keystore.jks -alias localhost \
  -import -file cert-signed

# Create truststore
keytool -keystore kafka.server.truststore.jks -alias CARoot \
  -import -file ca-cert
```

**server.properties:**

```properties
listeners=SSL://0.0.0.0:9093
advertised.listeners=SSL://kafka1.example.com:9093

ssl.keystore.location=/var/private/ssl/kafka.server.keystore.jks
ssl.keystore.password=password
ssl.key.password=password
ssl.truststore.location=/var/private/ssl/kafka.server.truststore.jks
ssl.truststore.password=password

ssl.client.auth=required
ssl.enabled.protocols=TLSv1.2,TLSv1.3
```

### SASL Authentication

**server.properties (SASL/PLAIN):**

```properties
listeners=SASL_SSL://0.0.0.0:9094
security.inter.broker.protocol=SASL_SSL
sasl.mechanism.inter.broker.protocol=PLAIN
sasl.enabled.mechanisms=PLAIN

listener.name.sasl_ssl.plain.sasl.jaas.config=org.apache.kafka.common.security.plain.PlainLoginModule required \
  username="admin" \
  password="admin-secret" \
  user_admin="admin-secret" \
  user_alice="alice-secret";
```

### Authorization (ACLs)

```bash
# Add ACL for topic
kafka-acls.sh --bootstrap-server localhost:9092 \
  --add --allow-principal User:alice \
  --operation Read --operation Write \
  --topic my-topic

# Add ACL for consumer group
kafka-acls.sh --bootstrap-server localhost:9092 \
  --add --allow-principal User:alice \
  --operation Read \
  --group my-consumer-group

# List ACLs
kafka-acls.sh --bootstrap-server localhost:9092 --list
```

## Performance Tuning

### Broker Tuning

**OS-level:**

```bash
# File descriptors
ulimit -n 100000

# TCP settings
sysctl -w net.core.wmem_default=131072
sysctl -w net.core.rmem_default=131072
sysctl -w net.ipv4.tcp_wmem='4096 16384 4194304'
sysctl -w net.ipv4.tcp_rmem='4096 87380 4194304'

# Swappiness
sysctl -w vm.swappiness=1

# Dirty pages
sysctl -w vm.dirty_ratio=80
sysctl -w vm.dirty_background_ratio=5
```

**Kafka configuration:**

```properties
# Increase threads
num.network.threads=16
num.io.threads=32

# Increase batch processing
log.flush.interval.messages=10000
log.flush.interval.ms=1000

# Optimize segment size
log.segment.bytes=1073741824
```

### Producer Tuning

```java
// Throughput-optimized
props.put("batch.size", 65536);
props.put("linger.ms", 100);
props.put("compression.type", "lz4");
props.put("buffer.memory", 134217728);

// Latency-optimized
props.put("batch.size", 0);
props.put("linger.ms", 0);
props.put("acks", "1");
```

### Consumer Tuning

```java
// Throughput-optimized
props.put("fetch.min.bytes", 50000);
props.put("fetch.max.wait.ms", 500);
props.put("max.poll.records", 1000);

// Latency-optimized
props.put("fetch.min.bytes", 1);
props.put("fetch.max.wait.ms", 0);
props.put("max.poll.records", 100);
```

## Disaster Recovery

### Multi-Datacenter Replication

**MirrorMaker 2 configuration:**

```properties
# Clusters
clusters = primary, backup
primary.bootstrap.servers = primary-kafka:9092
backup.bootstrap.servers = backup-kafka:9092

# Replication flows
primary->backup.enabled = true
primary->backup.topics = .*

# Consumer settings
primary->backup.groups = .*
```

**Start MirrorMaker 2:**

```bash
bin/connect-mirror-maker.sh mm2.properties
```

### Backup and Restore

**Topic backup:**

```bash
# Export topic data
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic my-topic --from-beginning \
  --max-messages 1000000 > backup.txt

# Restore
kafka-console-producer.sh --bootstrap-server localhost:9092 \
  --topic my-topic < backup.txt
```

## Maintenance Operations

### Rolling Restart

```bash
# For each broker:
1. Stop broker
2. Wait for under-replicated partitions to recover
3. Start broker
4. Verify broker is in-sync
5. Move to next broker
```

### Partition Rebalancing

```bash
# Generate reassignment plan
kafka-reassign-partitions.sh --bootstrap-server localhost:9092 \
  --topics-to-move-json-file topics.json \
  --broker-list "0,1,2" \
  --generate

# Execute reassignment
kafka-reassign-partitions.sh --bootstrap-server localhost:9092 \
  --reassignment-json-file reassignment.json \
  --execute

# Verify
kafka-reassign-partitions.sh --bootstrap-server localhost:9092 \
  --reassignment-json-file reassignment.json \
  --verify
```

### Expanding Cluster

```bash
# Add new broker
1. Configure new broker with unique broker.id
2. Start broker
3. Create reassignment plan to move partitions
4. Execute reassignment
5. Monitor replication progress
```

## Troubleshooting

### Common Issues

**Under-replicated partitions:**
- Check broker health and network connectivity
- Verify disk space availability
- Review broker logs for errors
- Check `replica.lag.time.max.ms` setting

**High consumer lag:**
- Increase consumer instances
- Optimize processing logic
- Tune `fetch.min.bytes` and `fetch.max.wait.ms`
- Check for rebalancing issues

**Out of memory errors:**
- Increase heap size (max 8GB)
- Tune page cache usage
- Review retention settings
- Check for topic hot spots

### Log Analysis

```bash
# Search for errors
grep ERROR /var/log/kafka/server.log

# Find slow requests
grep "Request.*completed.*took.*ms" /var/log/kafka/server.log | \
  awk '{if ($NF > 1000) print}'

# Check ISR shrinking
grep "Shrinking ISR" /var/log/kafka/server.log
```

## Best Practices

1. **Always use replication factor 3** in production
2. **Set `min.insync.replicas=2`** with RF=3
3. **Monitor under-replicated partitions** continuously
4. **Use rack awareness** for multi-AZ deployments
5. **Implement proper retention policies** based on use case
6. **Enable JMX monitoring** on all brokers
7. **Regular backup of metadata** (ZooKeeper or KRaft)
8. **Test failover scenarios** regularly
9. **Capacity plan for 2x growth**
10. **Document runbooks** for common operations
