from abc import ABC, abstractmethod

class BaseDatasetLoader(ABC):

    def __init__(self, dataset_path):
        self.dataset_path = dataset_path


    @abstractmethod
    def laod_metadata(self):
        pass

    @abstractmethod
    def dataset_info(self):
        pass