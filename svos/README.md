# Natural language annotations for the Oops! dataset

This archive contains various files with annotations or information on annotations gathered on Amazon Mechanical Turk. We ask workers to describe "What was the goal of this video?" as well as "What went wrong?" for over 8,000 videos in our dataset. We provide the following annotation files:

## train.json, val.json

The files that contain the annotations. Their format is:
 
 ```
{
    "filename": [
        {
            "goal": "...", "wentwrong": "...",
            "kgoalsvos": [...], "kwentwrongsvos": [...]
        },
         ...
        ], 
    ...
}
```

`goal` and `wentwrong` contain the raw sentences and `k*svos` contain the processed lists of SVOs. We label each video by 2 different workers, so top-level dictionary values are length-2 lists.

## vocab.json, corrections.json

`vocab.json` is a sorted, processed list of lemmatized vocabulary tokens **on detected SVOs** (that is, **not** on the entire natural language sentences). 
`corrections.json` contains the results of running a spell-checking algorithm on worker-provided annotations. Misspellings are removed from the vocabulary but preserved in the original annotation files (described below). In training, to convert an SVO triple into a list of vocabulary IDs, we run:

```
[vocab.index(w if w in vocab else self.svo_corrs[w]) for w in svo]
```

A similar process can be used to spell-check and tokenize full sentences.

### en_full.txt

A word frequency listing file we use as input to the spell-checker library (`pip install pyspellchecker`).

##  *_freq.txt

A listing of tokens (or SVO triples) by frequency, descended, as described by filename.

