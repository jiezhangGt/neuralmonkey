from typing import Any, Callable, Dict, Iterable, Iterator, List

import numpy as np


# pylint: disable=too-few-public-methods
class Preprocess:
    """Preprocessor transorming two series into series of edit operations."""

    def __init__(self, source_id: str, target_id: str) -> None:
        self._source_id = source_id
        self._target_id = target_id

    def __call__(
            self,
            iterators: Dict[str, Callable[[], Iterator[List[str]]]]
    ) -> Iterator[List[str]]:
        source_series = iterators[self._source_id]()
        target_series = iterators[self._target_id]()

        for src_seq, tgt_seq in zip(source_series, target_series):
            yield convert_to_edits(src_seq, tgt_seq)


class Postprocess:
    """Proprocessor applying edit operations on a series."""

    def __init__(
            self,
            source_id: str,
            edits_id: str) -> None:

        self._source_id = source_id
        self._edits_id = edits_id

    def __call__(self,
                 dataset: Dict[str, Iterable[Any]],
                 generated: Dict[str, Iterable[Any]]) -> List[List[str]]:

        if self._source_id not in dataset:
            raise ValueError("Source series not present in the input dataset")

        if self._edits_id not in generated:
            raise ValueError("Edits series not present in the output dataset")

        source_series = dataset[self._source_id]
        edits_series = generated[self._edits_id]

        reconstructed = []
        for src_seq, edit_seq in zip(source_series, edits_series):
            reconstructed.append(reconstruct(src_seq, edit_seq))

        return reconstructed
# pylint: enable=too-few-public-methods


KEEP = "<keep>"
DELETE = "<delete>"


def convert_to_edits(source: List[str], target: List[str]) -> List[str]:
    lev = np.zeros([len(source) + 1, len(target) + 1])
    edits = [[[] for _ in range(len(target) + 1)]
             for _ in range(len(source) + 1)]  # type: List[List[List[str]]]

    for i in range(len(source) + 1):
        lev[i, 0] = i
        edits[i][0] = [DELETE for _ in range(i)]

    for j in range(len(target) + 1):
        lev[0, j] = j
        edits[0][j] = target[:j]

    for j in range(1, len(target) + 1):
        for i in range(1, len(source) + 1):

            if source[i - 1] == target[j - 1]:
                keep_cost = lev[i - 1, j - 1]
            else:
                keep_cost = np.inf

            delete_cost = lev[i - 1, j] + 1
            insert_cost = lev[i, j - 1] + 1

            lev[i, j] = min(keep_cost, delete_cost, insert_cost)

            if lev[i, j] == keep_cost:
                edits[i][j] = edits[i - 1][j - 1] + [KEEP]

            elif lev[i, j] == delete_cost:
                edits[i][j] = edits[i - 1][j] + [DELETE]

            else:
                edits[i][j] = edits[i][j - 1] + [target[j - 1]]

    return edits[-1][-1]


def reconstruct(source: List[str], edits: List[str]) -> List[str]:
    index = 0
    target = []

    for edit in edits:
        if edit == KEEP:
            if index < len(source):
                target.append(source[index])
            index += 1

        elif edit == DELETE:
            index += 1

        else:
            target.append(edit)

    # we may have created a shorter sequence of edit ops due to the
    # decoder limitations -> now copy the rest of source
    if index < len(source):
        target.extend(source[index:])

    return target
