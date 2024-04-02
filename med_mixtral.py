# -*- coding: utf-8 -*-
"""med_mixtral.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/14-9S09IvuL6ULhnEAl2EOkKRsA4si_dw

# **MedMixtral: LLM Fine-Tuning with Predibase**

This quickstart will show you how to prompt, fine-tune, and deploy LLMs in Predibase. We'll be following a code generation use case where our end result will be a fine-tuned Mixtral model that takes in natural language as input and returns code as output.
"""

!pip install -U predibase --quiet
!pip install -q -U transformers bert-score evaluate

"""# **Setup**

You'll first need to initialize your PredibaseClient object and configure your API token.
"""

from predibase import PredibaseClient

pc = PredibaseClient(token="API_KEY")

"""# **Prompt a deployed LLM**

For our code generation use case, let's first see how Mixtral performs out of the box.

If you are in the Predibase SaaS environment, you have access to shared [serverless LLM deployments](https://docs.predibase.com/ui-guide/llms/query-llm/shared_deployments), including Llama 2 7B.

If you are in a VPC environment, you'll need to first [deploy a pretrained LLM](https://docs.predibase.com/user-guide/inference/dedicated_deployments#pretrained-llm-deployment).
"""

llm_deployment = pc.LLM("pb://deployments/mixtral-8x7b-instruct-v0-1")
result: list = llm_deployment.prompt("""
    Answer the following question shortly.

    ### Question: Malaria relapse common with which type plasmodium species?

    ### Answer:
""", max_new_tokens=256)
print(result.response)

"""# **Fine-tune a pretrained LLM**

Next we'll upload a dataset and fine-tune to see if we can get better performance.

The [MedMCQA](https://github.com/medmcqa/medmcqa) dataset is used for fine-tuning large language models to follow instructions to produce code from natural language and consists of the following columns:

- `question` that describes a question
- `exp` when additional context is required for the instruction
- the expected `output`


For the sake of this quickstart, we've created a version of the Code Alpaca dataset with fewer rows so that the model trains significantly faster.

**Now we will perform the following actions to start our fine-tuning job:**
1. Upload the dataset to Predibase for training
2. Create a prompt template to use for fine-tuning
3. Select the LLM we want to fine-tune
4. Kick off the fine-tuning job
"""

# Upload the dataset to Predibase (estimated time: 2 minutes due to creation of Predibase dataset with dataset profile)
# If you've already uploaded the dataset before, you can skip uploading and get the dataset directly with
dataset = pc.get_dataset("med_train", "file_uploads")
#dataset = pc.upload_dataset("xzy.csv")

dataset

# Define the template used to prompt the model for each example
# Note the 4-space indentation, which is necessary for the YAML templating.
prompt_template = """
    Given a passage, you need to accurately identify and extract relevant spans of text that answer specific questions. Provide concise and coherent responses based on the information present in the passage as well as a reasonable coherent explanation for your response.
    ### Passage: {exp}

    ### Question: {question}

    ### Answer:
"""

# Specify the Huggingface LLM you want to fine-tune
# Kick off a fine-tuning job on the uploaded dataset
llm = pc.LLM("hf://mistralai/Mixtral-8x7B-Instruct-v0.1")
job = llm.finetune(
    prompt_template=prompt_template,
    target="answer",
    dataset=dataset,
    repo="med_mixtral"
)

# Wait for the job to finish and get training updates and metrics
model = job.get()

"""# **Prompt your fine-tuned LLM**

Predibase supports both real-time inference, as well as [batch inference](https://docs.predibase.com/user-guide/inference/batch_prediction).

#### **Real-time inference using _LoRAX_** (Recommended)

[LoRA eXchange (LoRAX)](https://predibase.com/blog/lorax-the-open-source-framework-for-serving-100s-of-fine-tuned-llms-in) allows you to prompt your fine-tuned LLM without needing to create a new deployment for each model you want to prompt. Predibase automatically loads your fine-tuned weights on top of a shared LLM deployment on demand. While this means that there will be a small amount of additional latency, the benefit is that a single LLM deployment can support many different fine-tuned model versions without requiring additional compute.

Note: Inference using dynamic adapter deployments is available to both SaaS and VPC users. Predibase provides shared [serverless base LLM deployments](https://docs.predibase.com/user-guide/inference/serverless_deployments) for use in our SaaS environment. VPC users need [deploy their own base model](https://docs.predibase.com/user-guide/inference/dedicated_deployments#pretrained-llm-deployment).
"""

# Since our model was fine-tuned from a Llama-2-7b base, we'll use the shared deployment with the same model type.
base_deployment = pc.LLM("pb://deployments/mixtral-8x7b-instruct-v0-1")

# Now we just specify the adapter to use, which is the model we fine-tuned.
model = pc.get_model("med_mixtral")
adapter_deployment = base_deployment.with_adapter(model)

question_exp = "This is a single choice question. You need to choose one of those options: 1- Leukemoid reaction, 2- Leukopenia, 3- Myeloid metaplasia, 4- Neutrophilia. Which one is true?"
question = "A 40-year-old man presents with 5 days of productive cough and fever. Pseudomonas aeruginosa is isolated from a pulmonary abscess. CBC shows an acute effect characterized by marked leukocytosis (50,000 mL) and the differential count reveals a shift to left in granulocytes. Which of the following terms best describes these hematologic findings?"

# Recall that our model was fine-tuned using a template that accepts an {instruction}
# and an {input}. This template is automatically applied when prompting.
result = adapter_deployment.prompt(
    {"exp": question_exp,
    "question": question},
    max_new_tokens=256)

print(result.response)

import pandas as pd

dataset_test = pd.read_csv("med_test.csv")
dataset_test.head()

data_subset = dataset_test[:]

data_subset.shape

for ind in data_subset.index:
    #exp = data_subset['exp'][ind]
    exp = "This is a medical exam test and here is the explanation of question: "+str(data_subset['exp'][ind])
    d= {"exp":exp, "question":data_subset['question'][ind]}
    print(d)

for ind in data_subset.index:
    #exp = data_subset['exp'][ind]
    exp = "This is a medical exam test and here might be the explanation of question: \'"+str(data_subset['exp'][ind])+" .\' You must definetely select one of these options, \
    option 1: " +data_subset['opa'][ind]+ " , option 2: " +data_subset['opb'][ind]+ " , option 3: " +data_subset['opc'][ind]+ " , option 4: " + data_subset['opd'][ind]
    d= {"exp":exp, "question":data_subset['question'][ind]}
    print(d)

len(data_subset)

from tqdm.auto import tqdm
#inference for test dataset
pbar = tqdm(data_subset.index)

answers = []
for ind in data_subset.index:
    exp = "This is a medical exam test and here might be the explanation of question: \'"+str(data_subset['exp'][ind])+" .\' You must definetely select one of these options, \
    option 1: " +data_subset['opa'][ind]+ " , option 2: " +data_subset['opb'][ind]+ " , option 3: " +data_subset['opc'][ind]+ " , option 4: " + data_subset['opd'][ind]
    prompt= {"exp":exp, "question":data_subset['question'][ind]}
    #prompt = {"exp":data_subset['exp'][ind], "question":data_subset['question'][ind]}
    answer = adapter_deployment.prompt(prompt, temperature= 0.1, max_new_tokens=256)
    answers.append(answer.response)
    pbar.update(1)
pbar.close()

#evaluate with bert-score using distilbert model
from evaluate import load
import numpy as np
bertscore = load("bertscore")
predictions = answers
references = list(data_subset["answer"])
results = bertscore.compute(predictions=predictions, references=references, model_type="distilbert-base-uncased")
print("precision: ",round(np.mean(list(results["precision"])),5))
print("recall: ",round(np.mean(list(results["recall"])),5))
print("f1: ",round(np.mean(list(results["f1"])),5))

data_subset["chosen_answer"] = answers

data_subset["bert_score_f1"] = list(results["f1"])

data_subset.head(3)

from evaluate import load
import numpy as np
bertscore = load("bertscore")
predictions = answers
references = list(data_subset["opa"])
results = bertscore.compute(predictions=predictions, references=references, model_type="distilbert-base-uncased")
print("precision: ",round(np.mean(list(results["precision"])),5))
print("recall: ",round(np.mean(list(results["recall"])),5))
print("f1: ",round(np.mean(list(results["f1"])),5))

data_subset["opa_score"] = list(results["f1"])

from evaluate import load
import numpy as np
bertscore = load("bertscore")
predictions = answers
references = list(data_subset["opb"])
results = bertscore.compute(predictions=predictions, references=references, model_type="distilbert-base-uncased")
print("precision: ",round(np.mean(list(results["precision"])),5))
print("recall: ",round(np.mean(list(results["recall"])),5))
print("f1: ",round(np.mean(list(results["f1"])),5))

data_subset["opb_score"] = list(results["f1"])

from evaluate import load
import numpy as np
bertscore = load("bertscore")
predictions = answers
references = list(data_subset["opc"])
results = bertscore.compute(predictions=predictions, references=references, model_type="distilbert-base-uncased")
print("precision: ",round(np.mean(list(results["precision"])),5))
print("recall: ",round(np.mean(list(results["recall"])),5))
print("f1: ",round(np.mean(list(results["f1"])),5))

data_subset["opc_score"] = list(results["f1"])

from evaluate import load
import numpy as np
bertscore = load("bertscore")
predictions = answers
references = list(data_subset["opd"])
results = bertscore.compute(predictions=predictions, references=references, model_type="distilbert-base-uncased")
print("precision: ",round(np.mean(list(results["precision"])),5))
print("recall: ",round(np.mean(list(results["recall"])),5))
print("f1: ",round(np.mean(list(results["f1"])),5))

data_subset["opd_score"] = list(results["f1"])

data_subset.head(1)

data_subset.dtypes

import operator

chosen_op = []
for ind in data_subset.index:
    options = {'1': data_subset['opa_score'][ind] , '2': data_subset['opb_score'][ind] , '3': data_subset['opc_score'][ind] , '4': data_subset['opd_score'][ind]}
    selection = np.int64(max(options.items(), key=operator.itemgetter(1))[0])
    chosen_op.append(selection)

data_subset["chosen_op"] = chosen_op

from sklearn import metrics

Accuracy = metrics.accuracy_score(data_subset["cop"], data_subset["chosen_op"])
Accuracy

confusion_matrix = metrics.confusion_matrix(data_subset["cop"], data_subset["chosen_op"])
confusion_matrix

data_subset[["cop","chosen_op"]]

data_subset.to_csv('mixtral_result.csv', index=False)

data_subset.to_excel('mixtral_test.xlsx')