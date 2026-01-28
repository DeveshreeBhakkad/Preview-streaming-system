import os
import random
import csv


def generate_sample():
    """
    Generate a single synthetic network sample
    """

    bandwidth = random.uniform(300, 5000)      # kbps
    latency = random.uniform(20, 300)           # ms
    jitter = random.uniform(1, 50)               # ms
    packet_loss = random.uniform(0, 5)           # %

    # Rule-based buffer decision (ground truth)
    if bandwidth < 800 or latency > 200 or packet_loss > 3:
        forward_buffer = 5
    elif bandwidth < 1500 or latency > 120:
        forward_buffer = 3
    else:
        forward_buffer = 2

    return [
        round(bandwidth, 2),
        round(latency, 2),
        round(jitter, 2),
        round(packet_loss, 2),
        forward_buffer
    ]


def generate_dataset(num_samples=1000):
    header = [
        "bandwidth_kbps",
        "latency_ms",
        "jitter_ms",
        "packet_loss_pct",
        "forward_buffer_chunks"
    ]

    file_path = os.path.join(os.path.dirname(__file__), "network_buffer_data.csv")

    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for _ in range(num_samples):
            writer.writerow(generate_sample())



if __name__ == "__main__":
    generate_dataset()
    print("Synthetic network dataset generated: network_buffer_data.csv")
