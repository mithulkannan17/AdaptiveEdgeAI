class SampleIDGenerator:

    def __init__(self):
        self.counter = {}

    def generate(self, dataset):

        if dataset not in self.counter:
            self.counter[dataset] = 1

        sample_id = f"{dataset}_{self.counter[dataset]:06d}"

        self.counter[dataset] += 1

        return sample_id