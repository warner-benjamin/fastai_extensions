#AUTOGENERATED! DO NOT EDIT! file to edit: ./BatchLossFilter.ipynb (unless otherwise specified)

from fastai.basic_train import *
import functools
from functools import partial
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="torch.nn.functional")
from IPython.display import display, HTML
display(HTML("<style>.container { width:100% !important; }</style>"))



import math

class BatchLossFilterCallback(LearnerCallback):
    _order = -20

    def __init__(self, learn:Learner, min_sample_perc:float=0., min_loss_perc:float=0.):
        super().__init__(learn)
        assert min_sample_perc >0. or min_loss_perc > 0., 'min_sample_perc <= 0 and min_loss_perc <= 0'
        self.min_sample_perc, self.min_loss_perc = min_sample_perc, min_loss_perc
        self.learn = learn
        self.model = learn.model
        self.crit = learn.loss_func
        if hasattr(self.crit, 'reduction'):  self.red = self.crit.reduction
        self.sel_losses_sum, self.losses_sum = 0., 0.
        self.sel_samples, self.samples = 0., 0.
        self.recorder.add_metric_names(["loss_perc", "samp_perc"])

    def on_epoch_begin(self, **kwargs):
        "Set the inner value to 0."
        self.sel_losses_sum, self.losses_sum = 0., 0.
        self.sel_samples, self.samples = 0., 0.

    def on_batch_begin(self, last_input, last_target, train, epoch, **kwargs):
        if not train or epoch == 0: return
        if hasattr(self.crit, 'reduction'):  setattr(self.crit, 'reduction', 'none')
        with torch.no_grad():  self.losses = np.array(self.crit(self.model(last_input), last_target))
        if hasattr(self.crit, 'reduction'):  setattr(self.crit, 'reduction', self.red)
        self.get_loss_idxs()
        self.sel_losses_sum += self.losses[self.idxs].sum()
        self.losses_sum += self.losses.sum()
        self.sel_samples += len(self.idxs)
        self.samples += len(self.losses)
        return {"last_input": last_input[self.idxs], "last_target": last_target[self.idxs]}

    def on_epoch_end(self, epoch, last_metrics, **kwargs):
        loss_perc = self.sel_losses_sum / self.losses_sum if epoch > 0 else 1.
        sample_perc = self.sel_samples / self.samples if epoch > 0 else 1.
        return add_metrics(last_metrics, [loss_perc, sample_perc])

    def on_train_end(self, **kwargs):
        """At the end of training this calleback will be removed"""
        if hasattr(self.learn.loss_func, 'reduction'):  setattr(self.learn.loss_func, 'reduction', self.red)
        drop_cb_fn(self.learn, 'BatchLossFilterCallback')

    def get_loss_idxs(self):
        idxs = np.argsort(self.losses)[::-1]
        sample_max = math.ceil(len(idxs) * self.min_sample_perc)
        self.losses /= self.losses.sum()
        loss_max = np.argmax(self.losses[idxs].cumsum() >= self.min_loss_perc) + 1
        self.idxs =  list(idxs[:max(sample_max, loss_max)])


def drop_cb_fn(learn, cb_name:str)->None:
    cbs = []
    for cb in learn.callback_fns:
        if isinstance(cb, functools.partial): cbn = cb.func.__name__
        else: cbn = cb.__name__
        if cbn != cb_name: cbs.append(cb)
    learn.callback_fns = cbs


def batch_loss_filter(learn:Learner, min_sample_perc:float=0., min_loss_perc:float=.9)->Learner:
    learn.callback_fns.append(partial(BatchLossFilterCallback, min_sample_perc=min_sample_perc,
                                      min_loss_perc=min_loss_perc))
    return learn

Learner.batch_loss_filter = batch_loss_filter