from typing import Dict, List, Set, Union

from typeguard import check_argument_types

from neuralmonkey.runners.base_runner import (
    BaseRunner, Executable, FeedDict, ExecutionResult, NextExecute)
from neuralmonkey.model.model_part import ModelPart
from neuralmonkey.decoders.autoregressive import AutoregressiveDecoder
from neuralmonkey.decoders.classifier import Classifier
from neuralmonkey.trainers.generic_trainer import GenericTrainer

# pylint: disable=invalid-name
SupportedDecoder = Union[AutoregressiveDecoder, Classifier]
# pylint: enable=invalid-name


class GradientRunExecutable(Executable):

    def __init__(self,
                 all_coders: Set[ModelPart],
                 fetches: FeedDict) -> None:
        self._all_coders = all_coders
        self._fetches = fetches

        self.result = None

    def next_to_execute(self) -> NextExecute:
        """Get the feedables and tensors to run."""
        return self._all_coders, self._fetches, []

    def collect_results(self, results: List[Dict]) -> None:
        assert len(results) == 1

        for sess_result in results:
            gradient_dict = {}
            tensor_names = [t.name for t in self._fetches["gradients"]]
            for name, val in zip(tensor_names, sess_result["gradients"]):
                gradient_dict[name] = val

        self.result = ExecutionResult(
            outputs=[gradient_dict],
            losses=[],
            scalar_summaries=None,
            histogram_summaries=None,
            image_summaries=None)


class GradientRunner(BaseRunner[SupportedDecoder]):

    def __init__(self,
                 output_series: str,
                 trainer: GenericTrainer,
                 decoder: SupportedDecoder) -> None:
        check_argument_types()
        BaseRunner[AutoregressiveDecoder].__init__(
            self, output_series, decoder)

        self._gradients = trainer.gradients

    # pylint: disable=unused-argument
    def get_executable(self,
                       compute_losses: bool,
                       summaries: bool,
                       num_sessions: int) -> GradientRunExecutable:
        fetches = {"gradients": [g[1] for g in self._gradients]}

        return GradientRunExecutable(self.all_coders, fetches)
    # pylint: enable=unused-argument

    @property
    def loss_names(self) -> List[str]:
        return []