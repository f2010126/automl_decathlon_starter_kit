import datetime
import logging
import numpy as np
import os
import sys
import time
import math

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.autograd import Variable

# seeding randomness for reproducibility
np.random.seed(42)
torch.manual_seed(1)

# PyTorch Model class
class TorchModel3D(nn.Module):
  def __init__(self, input_shape, output_dim, channels=3):
    ''' 3D CNN Model with no of CNN layers depending on the input size'''
    super(TorchModel3D, self).__init__()
    self.conv1 = nn.Conv3d(
        channels, 16, kernel_size=3, stride=1, padding=1, bias=False
    )
    fc_size, _ = self.get_fc_size(input_shape)
    self.fc = nn.Linear(fc_size, output_dim)

  def forward_cnn(self, x):
    x = self.conv1(x)
    return x

  def get_fc_size(self, input_shape):
    ''' function to get the size for Linear layers
    with given number of CNN layers
    '''

    sample_input = Variable(torch.rand((20, 1, 64, 64)))
    output_feat = self.forward_cnn(sample_input.unsqueeze(dim=1))
    print(f'Output Feat: {output_feat.shape}')
    out_shape = output_feat.shape
    print(f'Output Shape: {out_shape}')
    n_size = output_feat.data.view(1, -1).size(1)
    print(f'n_size, out_shape {n_size}, {out_shape}')
    return n_size, out_shape

  def forward(self, x):
    x = self.forward_cnn(x)
    x = x.view(x.size(0), -1)
    x = self.fc(x)
    return x

class Model:

    ##############################################################################
    #### The 3 methods (__init__, train, test) should always be implemented ####
    ##############################################################################
    def __init__(self, metadata):
        """
                The initalization procedure for your method given the metadata of the task
                """
        """
        Args:
          metadata: an DecathlonMetadata object. Its definition can be found in
              ingestion/dev_datasets.py
        """
        self.metadata_ = metadata
        # Getting details of the data from meta data
        # Product of output dimensions in case of multi-dimensional outputs...
        self.output_dim = math.prod(self.metadata_.get_output_shape())

        row_count, col_count = self.metadata_.get_tensor_shape()[2:4]
        channel = self.metadata_.get_tensor_shape()[1]
        sequence_size = self.metadata_.get_tensor_shape()[0]

        self.num_train = self.metadata_.size()
        # Getting the device available
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(
            "Device Found = ", self.device, "\nMoving Model and Data into the device..."
        )

        self.input_shape = (sequence_size, channel, row_count, col_count)
        print("\n\nINPUT SHAPE = sequence_size, channel, row_count, col_count ->", self.input_shape)
        print("\n\nOUTPUT DIM AKA # of Classes = ", self.output_dim)
        # determine model structure based on the data
        spacetime_dims = np.count_nonzero(np.array(self.input_shape)[[0, 2, 3]] != 1)
        logger.info(f"Using Model of dimension {spacetime_dims}")

        # getting an object for the PyTorch Model class for Model Class
        # use CUDA if available
        # TODO: ADD THE MODEL HERE ACCORDING TO spacetime_dims
        if spacetime_dims == 1:
            self.model = TorchModel3D(self.input_shape, self.output_dim,channel)
        elif spacetime_dims == 2:
            self.model = TorchModel3D(self.input_shape, self.output_dim,channel)
        elif spacetime_dims == 3:
            self.model = TorchModel3D(self.input_shape, self.output_dim,channel)
        elif spacetime_dims == 0:
            self.model = TorchModel3D(self.input_shape, self.output_dim,channel)
        else:
            raise NotImplementedError

        print(self.model)
        self.model.to(self.device)
        
        # PyTorch Optimizer and Criterion
        if self.metadata_.get_task_type() == "continuous":
            self.criterion = nn.MSELoss()
        elif self.metadata_.get_task_type() == "single-label":
            self.criterion = nn.CrossEntropyLoss()
        elif self.metadata_.get_task_type() == "multi-label":
            self.criterion = nn.BCEWithLogitsLoss()
        else:
            raise NotImplementedError

        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-2)

        # Attributes for managing time budget
        # Cumulated number of training steps
        self.birthday = time.time()
        self.total_train_time = 0
        self.total_test_time = 0

        # no of examples at each step/batch
        self.train_batch_size = 64
        self.test_batch_size = 64

    ## DO NOT MODIFY
    def get_dataloader(self, dataset, batch_size, split):
        """Get the PyTorch dataloader. Do not modify this method.
        Args:
          dataset:
          batch_size : batch_size for training set

        Return:
          dataloader: PyTorch Dataloader
        """
        if split == "train":
            dataloader = DataLoader(
                dataset,
                dataset.required_batch_size or batch_size,
                shuffle=True,
                drop_last=False,
                collate_fn=dataset.collate_fn,
            )
        elif split == "test":
            dataloader = DataLoader(
                dataset,
                dataset.required_batch_size or batch_size,
                shuffle=False,
                collate_fn=dataset.collate_fn,
            )
        return dataloader

    def train(
            self, dataset, val_dataset=None, val_metadata=None, remaining_time_budget=None
    ):
        """
        The training procedure of your method given training data, validation data (which is only directly provided in certain tasks, otherwise you are free to create your own validation strategies), and remaining time budget for training.
        """

        """Train this algorithm on the Pytorch dataset.

        ****************************************************************************
        ****************************************************************************

        Args:
          dataset: a `DecathlonDataset` object. Each of its examples is of the form
                (example, labels)
              where `example` is a dense 4-D Tensor of shape
                (sequence_size, row_count, col_count, num_channels)
              and `labels` is a 1-D or 2-D Tensor

          val_dataset: a 'DecathlonDataset' object. Is not 'None' if a pre-split validation set is provided, in which case you should use it for any validation purposes. Otherwise, you are free to create your own validation split(s) as desired.

          val_metadata: a 'DecathlonMetadata' object, corresponding to 'val_dataset'.

          remaining_time_budget: time remaining to execute train(). The method
              should be tuned to fit within this budget.
        """

        logger.info("Begin training...")
        # If PyTorch dataloader for training set doen't already exists, get the train dataloader
        if not hasattr(self, "trainloader"):
            self.trainloader = self.get_dataloader(
                dataset,
                self.train_batch_size,
                "train",
            )

        train_start = time.time()
        # Training loop
        #TODO: Does this become a HP??
        epochs_to_train = 200  # may adjust as necessary
        self.trainloop(self.criterion, self.optimizer, epochs=epochs_to_train)
        train_end = time.time()

        # Update for time budget managing
        train_duration = train_end - train_start
        self.total_train_time += train_duration

        logger.info(
            "{} epochs trained. {:.2f} sec used. ".format(
                epochs_to_train, train_duration
            )
            + "Total time used for training: {:.2f} sec. ".format(self.total_train_time)
        )

        def test(self, dataset, remaining_time_budget=None):
            """Test this algorithm on the Pytorch dataloader.

            Args:
              Same as that of `train` method, except that the `labels` will be empty.
            Returns:
              predictions: A `numpy.ndarray` matrix of shape (sample_count, output_dim).
                  here `sample_count` is the number of examples in this dataset as test
                  set and `output_dim` is the number of labels to be predicted. The
                  values should be binary or in the interval [0,1].
            """

            test_begin = time.time()

            logger.info("Begin testing...")

            if not hasattr(self, "testloader"):
                self.testloader = self.get_dataloader(
                    dataset,
                    self.test_batch_size,
                    "test",
                )

            # get predictions from the test loop
            predictions = self.testloop(self.testloader)

            test_end = time.time()
            # Update some variables for time management
            test_duration = test_end - test_begin

            logger.info(
                "[+] Successfully made predictions. {:.2f} sec used. ".format(test_duration)
            )
            return predictions

    # Taken from the autodl code
        def trainloop(self, criterion, optimizer, epochs):
            """Training loop with no of given steps
            Args:
              criterion: PyTorch Loss function
              Optimizer: PyTorch optimizer for training
              epochs: No of epochs to train the model

            Return:
              None, updates the model parameters
            """
            self.model.train()
            data_iterator = iter(self.trainloader)
            for i in range(epochs):
                try:
                    images, labels = next(data_iterator)
                except StopIteration:
                    data_iterator = iter(self.trainloader)
                    images, labels = next(data_iterator)

                images = images.float().to(self.device)
                labels = labels.float().to(self.device)
                optimizer.zero_grad()

                log_ps = self.model(images)
                # is reshaping labels needed??
                loss = criterion(log_ps, labels)
                if hasattr(self, 'scheduler'):
                    self.scheduler.step(loss)
                loss.backward()
                optimizer.step()

        # Not from autodl code
        def testloop(self, dataloader):
            """
            Args:
              dataloader: PyTorch test dataloader

            Return:
              preds: Predictions of the model as Numpy Array.
            """
            preds = []
            with torch.no_grad():
                self.model.eval()
                for images, _ in iter(dataloader):
                    if torch.cuda.is_available():
                        images = images.float().cuda()
                    else:
                        images = images.float()
                    logits = self.model(images)

                    # Choose correct prediction type
                    if self.metadata_.get_task_type() == "continuous":
                        pred = logits
                    elif self.metadata_.get_task_type() == "single-label":
                        pred = torch.softmax(logits, dim=1).data
                    elif self.metadata_.get_task_type() == "multi-label":
                        pred = torch.sigmoid(logits).data
                    else:
                        raise NotImplementedError

                    preds.append(pred.cpu().numpy())

            preds = np.vstack(preds)
            return preds



def get_logger(verbosity_level):
    """Set logging format to something like:
    2019-04-25 12:52:51,924 INFO model.py: <message>
    """
    logger = logging.getLogger(__file__)
    logging_level = getattr(logging, verbosity_level)
    logger.setLevel(logging_level)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(filename)s: %(message)s"
    )
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging_level)
    stdout_handler.setFormatter(formatter)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)
    logger.propagate = False
    return logger


logger = get_logger("INFO")