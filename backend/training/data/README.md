# Training data

| File | Rows | What it is | Used for |
|---|---|---|---|
| `PROMISE_exp.csv` | 969 | Real requirements from 47 projects, labelled by the dataset's authors | 80% train, 20% test |
| `app_style_train.csv` | 100 | Short sentences written by hand for this project | Train only |
| `app_style_test.csv` | 55 | Short sentences written by hand for this project | Test only |

## PROMISE_exp

Lima, M., Valle, V., Costa, E., Lira, F. and Gadelha, B. "Software Engineering
Repositories: Expanding the PROMISE Database." SBES 2019. DOI: 10.1145/3350768.3350776

Downloaded from
<https://github.com/AleksandarMitrevski/se-requirements-classification>
(`1-exploratory-analysis/data/PROMISE_exp.csv`). Check the original source's terms before
redistributing the file outside this coursework.

## Why the app-style files exist

PROMISE is written formally ("The system shall..."). The LLM writes short sentences such as
"Users can log in.". A model trained only on PROMISE performed poorly on those sentences, so
hand-written examples in that style were added.

## Limitations

- The app-style files were written by the project author, not collected from clients or
  labelled independently. Their scores are only a sanity check, not published-quality results.
- `app_style_test.csv` was written before the model was retrained, and uses different domains
  from the training file. It is small, and each sentence is worth about 2% accuracy.
- The functional/non-functional boundary is sometimes a judgement call. For example, "Sessions
  must expire after 15 minutes" could be labelled either way.
