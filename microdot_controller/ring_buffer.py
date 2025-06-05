class RingBuffer:
    def __init__(self, size):
        self.size = size
        self.buffer = [0] * size
        self.index = 0
        self.count = 0

    def add(self, value):
        self.buffer[self.index] = value
        self.index = (self.index + 1) % self.size
        if self.count < self.size:
            self.count += 1

    def average(self):
        return sum(self.buffer) / self.count if self.count > 0 else 0

# # Example usage
# ring_buffer = RingBuffer(5)

# # Simulating sensor readings
# sensor_readings = [1,3]

# running_averages = []
# for reading in sensor_readings:
#     ring_buffer.add(reading)
#     running_averages.append(ring_buffer.average())

# running_averages
