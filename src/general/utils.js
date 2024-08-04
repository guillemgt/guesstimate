import fs from 'fs';


async function removeDuplicates(arr) {
    return [...new Set(arr)];
}

async function parallelCalls(fn, args, maxConcurrent) {
    let results = [];
    let processing = [];

    for (let arg of args) {
        const promise = fn(arg).then(result => {
            // Remove this promise from the processing list
            processing.splice(processing.indexOf(promise), 1);
            return result;
        });

        results.push(promise);
        processing.push(promise);

        if (processing.length >= maxConcurrent) {
            // Wait for one of the requests to finish before continuing
            await Promise.race(processing);
        }
    }

    // Wait for all remaining requests to finish
    return Promise.all(results);
}



async function wrap_prompt(user_prompt, system_prompt, prompt_examples, {examples_as_messages=false} = {}){

    let messages = [];
    messages.push({
        "role": "system",
        "content": system_prompt
    });

    if(!examples_as_messages){
        messages[0]["content"] += "\n\n\n# Examples\n";
    }

    for(let example of prompt_examples){
        let input_string;
        if(typeof example.input === 'object'){
            input_string = JSON.stringify(example.input);
        }else{
            input_string = "" + example.input;
        }

        let output_string;
        if(typeof example.output === 'object'){
            output_string = JSON.stringify(example.output);
        }else{
            output_string = "" + example.output;
        }
        
        if(examples_as_messages){
            messages.push({
                "role": "user",
                "content": input_string
            });
            messages.push({
                "role": "assistant",
                "content": output_string
            });
        }else{
            messages[0]["content"] += "Input: " + input_string + "\n";
            messages[0]["content"] += "Output: " + output_string + "\n\n";
        }
    }

    messages[0]["content"] = messages[0]["content"].trim();

    let user_string;
    if(typeof user_prompt === 'object'){
        user_string = JSON.stringify(user_prompt);
    }else{
        user_string = "" + user_prompt;
    }

    messages.push({
        "role": "user",
        "content": user_string
    });

    return messages;
}

async function count_votes(output, {good_keyword="good", bad_keyword="bad"} = {}){
    let votes_good = 0;
    let votes_bad = 0;

    if(!Array.isArray(output)){
        output = [output];
    }

    let argumentations = [];
    for(let choice of output){
        if(choice.finish_reason != "stop" && choice.finish_reason != "length"){
            console.log("Finish reason is not stop or length");
            continue;
        }

        argumentations.push(choice.message);

        let good_index = choice.message.toLowerCase().lastIndexOf(good_keyword)
        let bad_index = choice.message.toLowerCase().lastIndexOf(bad_keyword)

        if(good_index > bad_index){
            votes_good += 1;
        }else{
            votes_bad += 1;
        }
    }

    return [votes_good > votes_bad, argumentations];
}

async function filter_questions(questions, outputs, evaluation_file_path, {good_keyword="good", bad_keyword="bad"} = {}){
    let evaluations = []
    for(let i=0; i<outputs.length; i++){
        let output = outputs[i];
        let description = questions[i].description;
        let topic = questions[i].topic;
        let [success, argumentations] = await count_votes(output, {good_keyword: good_keyword, bad_keyword: bad_keyword});
        evaluations.push({
            "topic": topic,
            "description": description,
            "success": success,
            "argumentations": argumentations,
        });
    }

    fs.writeFileSync(evaluation_file_path, JSON.stringify(evaluations));

    let new_questions = [];
    for(let i=0; i<evaluations.length; i++){
        if(evaluations[i].success){
            new_questions.push(questions[i]);
        }
    }

    return new_questions;
}


function get_description(question){
    let desc = question.description_base;
    if(question.description_date){
        desc += " " + question.description_date;
    }
    if(question.description_unit){
        desc += " " + question.description_unit;
    }
    return desc;
}

export { removeDuplicates, parallelCalls, wrap_prompt, count_votes, filter_questions, get_description };