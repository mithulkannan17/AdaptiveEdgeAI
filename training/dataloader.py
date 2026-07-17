from torch.utils.data import DataLoader

from .dataset import EnvironmentalSoundDataset


class DatasetLoader:
    def create(
            self, 
            feature_paths,
            labels,
            batch_size=32,
            shuffle=True
    ):
        
        dataset = EnvironmentalSoundDataset(

            feature_paths,

            labels
        )

        loader = DataLoader(
            dataset,

            batch_size=batch_size,

            shuffle=shuffle
        )

        return loader