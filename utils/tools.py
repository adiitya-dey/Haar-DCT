import numpy as np
import torch
import matplotlib.pyplot as plt
import time
import torch.nn as nn
import math
import torch.nn.functional as F


plt.switch_backend('agg')


def adjust_learning_rate(optimizer, scheduler, epoch, args, printout=True):
    # lr = args.learning_rate * (0.2 ** (epoch // 2))
    if args.lradj == 'type1':
        lr_adjust = {epoch: args.learning_rate * (0.5 ** ((epoch - 1) // 1))}
    elif args.lradj == 'type2':
        lr_adjust = {
            2: 5e-5, 4: 1e-5, 6: 5e-6, 8: 1e-6,
            10: 5e-7, 15: 1e-7, 20: 5e-8
        }
    elif args.lradj == 'type3':
        lr_adjust = {epoch: args.learning_rate if epoch < 3 else args.learning_rate * (0.8 ** ((epoch - 3) // 1))}
    elif args.lradj == 'constant':
        lr_adjust = {epoch: args.learning_rate}
    elif args.lradj == '3':
        lr_adjust = {epoch: args.learning_rate if epoch < 10 else args.learning_rate*0.1}
    elif args.lradj == '4':
        lr_adjust = {epoch: args.learning_rate if epoch < 15 else args.learning_rate*0.1}
    elif args.lradj == '5':
        lr_adjust = {epoch: args.learning_rate if epoch < 25 else args.learning_rate*0.1}
    elif args.lradj == '6':
        lr_adjust = {epoch: args.learning_rate if epoch < 5 else args.learning_rate*0.1}  
    elif args.lradj == 'TST':
        lr_adjust = {epoch: scheduler.get_last_lr()[0]}
    
    if epoch in lr_adjust.keys():
        lr = lr_adjust[epoch]
        for param_group in optimizer.param_groups:
            param_group['lr'] = lr
        if printout: print('Updating learning rate to {}'.format(lr))


class EarlyStopping:
    def __init__(self, patience=7, verbose=False, delta=0):
        self.patience = patience
        self.verbose = verbose
        self.counter = 0
        self.best_score = None
        self.early_stop = False
        self.val_loss_min = np.Inf
        self.delta = delta

    def __call__(self, val_loss, model, path):
        score = -val_loss
        if self.best_score is None:
            self.best_score = score
            self.save_checkpoint(val_loss, model, path)
        elif score < self.best_score + self.delta:
            self.counter += 1
            print(f'EarlyStopping counter: {self.counter} out of {self.patience}')
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_score = score
            self.save_checkpoint(val_loss, model, path)
            self.counter = 0

    def save_checkpoint(self, val_loss, model, path):
        if self.verbose:
            print(f'Validation loss decreased ({self.val_loss_min:.6f} --> {val_loss:.6f}).  Saving model ...')
        torch.save(model.state_dict(), path + '/' + 'checkpoint.pth')
        self.val_loss_min = val_loss


class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class StandardScaler():
    def __init__(self, mean, std):
        self.mean = mean
        self.std = std

    def transform(self, data):
        return (data - self.mean) / self.std

    def inverse_transform(self, data):
        return (data * self.std) + self.mean


def visual(true, preds=None, name='./pic/test.pdf'):
    """
    Results visualization
    """
    plt.figure()
    plt.plot(true, label='GroundTruth', linewidth=2)
    if preds is not None:
        plt.plot(preds, label='Prediction', linewidth=2)
    plt.legend()
    plt.savefig(name, bbox_inches='tight')

def test_params_flop(model,x_shape):
    """
    If you want to thest former's flop, you need to give default value to inputs in model.forward(), the following code can only pass one argument to forward()
    """
    # model_params = 0
    # for parameter in model.parameters():
    #     model_params += parameter.numel()
    #     print('INFO: Trainable parameter count: {:.2f}M'.format(model_params / 1000000.0))
    # from ptflops import get_model_complexity_info
    # with torch.cuda.device(0):
    #     macs, params = get_model_complexity_info(model.cuda(), x_shape, as_strings=True, print_per_layer_stat=True)
    #     # print('Flops:' + flops)
    #     # print('Params:' + params)
    #     print('{:<30}  {:<8}'.format('Computational complexity: ', macs))
    #     print('{:<30}  {:<8}'.format('Number of parameters: ', params))
    from ptflops import get_model_complexity_info
    with torch.cuda.device(0):
        macs, params = get_model_complexity_info(model.cuda(), x_shape, as_strings=True, print_per_layer_stat=False)
        print('{:<30}  {:<8}'.format('Computational complexity: ', macs))
        print('{:<30}  {:<8}'.format('Number of parameters: ', params))
        return macs, params
    
class WaveletMSELoss(nn.Module):
    def __init__(self, alpha=1.0, beta=1.0):
        super(WaveletMSELoss, self).__init__()
        self.low_pass_filter = torch.tensor([1, 1], dtype=torch.float32) / math.sqrt(2)
        self.high_pass_filter = torch.tensor([1,-1], dtype=torch.float32) / math.sqrt(2)
        self.criterion = nn.MSELoss()
        

    def forward(self, y_pred, y_true):
        batch, length, channel = y_true.shape

        low_pass = self.low_pass_filter.reshape(1,1,-1).repeat(channel, 1, 1)
        high_pass = self.high_pass_filter.reshape(1,1,-1).repeat(channel, 1, 1)

        y_pred = y_pred.permute(0,2,1)
        y_true = y_true.permute(0,2,1)

        y_pred_A = F.conv1d(input=y_pred, weight=low_pass, stride=2, groups=channel)
        y_true_A = F.conv1d(input=y_true, weight=low_pass, stride=2, groups=channel)

        y_pred_D = F.conv1d(input=y_pred, weight=high_pass, stride=2, groups=channel)
        y_true_D = F.conv1d(input=y_true, weight=high_pass, stride=2, groups=channel)
        
        loss_approx = self.criterion(y_pred_A.permute(0,2,1), y_true_A.permute(0,2,1))
        loss_detail = self.criterion(y_pred_D.permute(0,2,1), y_true_D.permute(0,2,1))
        total_loss = 1.0 * loss_approx + 3.0 * loss_detail

        return total_loss



