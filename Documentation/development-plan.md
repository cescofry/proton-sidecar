# Development plan to build the tool

## Step 1:
build the tool using the provided product requirements and tech specs. (Other documents in Documets/ are a good reference to).
Do not try to build any of the sidecar applications. Spend minimal time on drafting the LLM.md file

## Step 2:
Build the acc-connector tool. Start by running `proton-sidecar init URL` to check that the file genration works
After that I will use the LLM.md on calude code to generate the scripts and manifests. 

## Step 3:
Retrospective. Based on the feedback of Step 2, we will work on improving the LLM.md file


# Methodology
For each step you are expected to perform the following:

## Build
Do the thinking and produce the code to achieve the task at hand. Follow best practices, produce documented and readable code, avoid duplication by extracting logic. Try to maintain the style currently used in the project

## Test
Run the current test suit, make sure the tests are up to date, create new tests based on the code that has been added

## Review
review the proposed changes, making sure they follow the product requirements and the tech specs.


## Repeat
If, according to the review, chnages are necessary, repeat the cycle of `Build`, `Test`, `Review`. Keep repeating until you are satisfied with the reviewed product.

