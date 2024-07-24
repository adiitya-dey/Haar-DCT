import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from layers.EchoStateNetwork import ESN
   


class Model(nn.Module):
    """
    DLinear
    """
    def __init__(self, configs):
        super(Model, self).__init__()
        self.seq_len = configs.seq_len
        self.pred_len = configs.pred_len
        self.window_len = configs.window_len
        self.reservoir_size = configs.reservoir_size
        self.washout = configs.washout


        self.input_seg = self.seq_len // self.window_len
        self.pred_seg = self.pred_len // self.window_len

        self.individual = configs.individual
        self.channels = configs.enc_in

        if self.individual:
            self.esn_layers = nn.ModuleList()
            self.readout_layers = nn.ModuleList()
            self.projection_layers = nn.ModuleList()

            for i in range(self.channels):
                self.esn_layers.append(ESN(reservoir_size=self.reservoir_size,
                                        activation=nn.Tanh(),
                                        input_size=self.window_len,
                                        )
                                    )

                self.readout_layers.append(nn.Linear(in_features=(self.input_seg - self.washout)*self.reservoir_size,
                                                    out_features=self.pred_seg*self.reservoir_size,
                                                    bias=True
                                                    )
                                            )

                self.projection_layers.append(nn.Linear(in_features=self.reservoir_size,
                                                        out_features=self.window_len,
                                                        bias=True
                                                        )
                                            )
        else:
        
            self.esn = ESN(reservoir_size=self.reservoir_size,
                            activation=nn.Tanh(),
                            input_size=self.window_len,
                            )
            

            self.readout = nn.Linear(in_features=(self.input_seg - self.washout)*self.reservoir_size,
                                    out_features=self.pred_seg*self.reservoir_size,
                                    bias=True)


            self.projection = nn.Linear(in_features=self.reservoir_size,
                                        out_features=self.window_len,
                                        bias=True)
            
    ## x: [Batch, Input length, Channel]
    def forward(self, x):
        
        if self.individual:
            # out: [Batch, Prediction length, Channels]
            out = torch.zeros(x.shape[0], x.shape[2], self.pred_len)

            # For each channel:
            for i in range(self.channels):
                output = x[:,:,i].clone()

                 ## Output x: [Batch, Input Segment, window length]
                output = output.reshape(output.shape[0], self.input_seg, self.window_len)

                ## Output x: [Batch, Input Segment, reservoir size]
                output = self.esn_layers[i](output)

                ## Output x: [Batch, (Input Segment - Washout), reservoir size]
                output = output[:, self.washout:, :]

                ## Flattening of batch sequences.
                ## Output x: [Batch, (Input Segment - Washout) * reservoir size)]
                output = output.view(output.shape[0], -1)

                ## Trainable Prediction/Readout layer.
                ## Output x: [Batch, Pred Segment, reservoir size]
                output = self.readout_layers[i](output)

                output = output.reshape(output.shape[0], self.pred_seg, self.reservoir_size)

                ## Trainable Projection Layer.
                ## output x: [Batch, Pred Length]
                output = self.projection_layers[i](output)
                output = output.reshape(output.shape[0], -1)

                out[:, i, :] = output

            x = out





        else:

            ## Output x: [Batch, Input Segment, window length]
            x = x.squeeze(-1)
            x = x.reshape(x.shape[0], self.input_seg, self.window_len)

            ## Output x: [Batch, Input Segment, reservoir size]
            x = self.esn(x)

            ## Output x: [Batch, (Input Segment - Washout), reservoir size]
            x = x[:, self.washout:, :]
            

            ## Flattening of batch sequences.
            ## Output x: [Batch, (Input Segment - Washout) * reservoir size)]
            x = x.view(x.shape[0], -1)

            ## Trainable Prediction/Readout layer.
            ## Output x: [Batch, Pred Segment, reservoir size]
            x = self.readout(x)

            
            x = x.reshape(x.shape[0], self.pred_seg, self.reservoir_size)

            ## Trainable Projection Layer.
            ## output x: [Batch, Pred Length]
            x = self.projection(x)
            x = x.reshape(x.shape[0], -1)

            # Add Channel to dimension.
            x = torch.unsqueeze(x, 1)

        return x.permute(0,2,1) # to [Batch, Output length, Channel]