import * as cheerio from 'cheerio';
import {encode, decode} from 'gpt-3-encoder'
import { config } from 'dotenv';
config();

import fs from 'fs';


/* =============================
    Calling APIs
   ============================= */

import { do_openai_requests, compute_price } from "./general/openai.js"
import { wrap_prompt } from "./general/utils.js"


/* =============================
    Main
   ============================= */

async function postprocess_answer(finish_reason, output, question){
    if(finish_reason != "stop" && finish_reason != "length"){
        console.log("Finish reason for stage 2 is not stop or length");
        return null;
    }

    // Copy the question
    let new_question = {};
    for(let key in question){
        new_question[key] = question[key];
    }

    new_question["description"] = output["description"];
    new_question["unit"] = output["units_of_measurement"];
    new_question["answer_is_approximate"] = output["answer_is_approximate"];
    if(output["value"] != null)
        new_question["answer"] = output["value"];
    else if(output["value_interval"] != null){
        new_question["answer"] = output["value_interval"];
        if(output["value_interval"][0] == output["value_interval"][1]){
            if(output["value_interval"][0] == null)
                return null;
            new_question["answer"] = output["value_interval"][0];
        }
    }else{
        return null;
    }


    return new_question;
}

async function main(params = {
    "input_path": "data/filter_clear.json",
    "output_path": "data/parse_number.json",
    "log_path": "/data/logs/parse_number/",
    "system_prompt_path": "prompts/parse_number_system.txt",
    "examples_prompt_path": "prompts/parse_number_examples.json",
    "temperature": 0.0,
}) {
    const questions = JSON.parse(fs.readFileSync(params.input_path));

    // Form the prompts
    const system_prompt = fs.readFileSync(params.system_prompt_path, 'utf8');
    const prompt_examples = JSON.parse(fs.readFileSync(params.examples_prompt_path, 'utf8'));

    let prompts = [];
    for(let question of questions){

        let prompt = await wrap_prompt({
            "description": question.description,
            "value": question.answer,
        }, system_prompt, prompt_examples);

        prompts.push(prompt);
    }
    
    fs.mkdirSync(params.log_path, { recursive: true });
    
    const batch_call_id = "parse_number";
    let [outputs, input_usage, output_usage] = await do_openai_requests(
        prompts,
        batch_call_id,
        params.log_path,
        {
            force_json: true,
            use_batch_api: true,
            temperature: params.temperature,
        }
    );
    console.log(input_usage, "IT,", output_usage, "OT,", compute_price(input_usage, output_usage) + "$");

    let new_questions = []
    for(let i=0; i<outputs.length; i++){
        let output = outputs[i];
        let question = questions[i];
        let finish_reason = output.finish_reason;
        let message = output.message;
        try{
            let new_question = await postprocess_answer(finish_reason, JSON.parse(message), question);
            if(new_question != null)
                new_questions.push(new_question);
        }catch(e){
            console.log(e);
        }
    }

    fs.writeFileSync(params.output_path, JSON.stringify(new_questions));
}

export { main };

// GPT-4o mini: $0.4067 for 3842 questions