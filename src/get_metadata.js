import { config } from 'dotenv';
config();

import fs from 'fs';



/* =============================
    Calling APIs
   ============================= */

import { do_openai_requests, compute_price } from "./general/openai.js"
import { wrap_prompt, get_description } from "./general/utils.js"

/* =============================
    Main
   ============================= */

async function postprocess_answer(finish_reason, output, question){
    if(finish_reason != "stop" && finish_reason != "length"){
        console.log("Finish reason for stage 2 is not stop or length");
        return null;
    }

    const categories = [
        "distance",
        "weight",
        "volume",
        "speed",
        "time",
        "date",
        "number",
        "proportion",
        "money",
    ]

    for(let category of categories){
        if(output.includes(category)){
            question["category"] = category;
            return question;
        }
    }

    question["category"] = "other";
    return question;
}

async function main(params = {
    "input_path": "data/filter_correct.json",
    "output_path": "data/get_metadata.json",
    "log_path": "/data/logs/get_metadata/",
    "system_prompt_path": "prompts/get_metadata_system.txt",
    "examples_prompt_path": "prompts/get_metadata_examples.json",
    "temperature": 0.0,
}) {
    const gather_questions = JSON.parse(fs.readFileSync(params.input_path));

    // Form the prompts
    const system_prompt = fs.readFileSync(params.system_prompt_path, 'utf8');
    const prompt_examples = JSON.parse(fs.readFileSync(params.examples_prompt_path, 'utf8'));

    let prompts = [];
    for(let question of gather_questions){

        let prompt = await wrap_prompt(get_description(question) + ": " + question.answer + (question.unit ? " " + question.unit : ""), system_prompt, prompt_examples);

        prompts.push(prompt);
    }
    
    fs.mkdirSync(params.log_path, { recursive: true });
    
    const batch_call_id = "get_metadata";
    let [outputs, input_usage, output_usage] = await do_openai_requests(
        prompts,
        batch_call_id,
        params.log_path,
        {
            force_json: false,
            use_batch_api: true,
            temperature: params.temperature,
        }
    );
    console.log(input_usage, "IT,", output_usage, "OT,", compute_price(input_usage, output_usage) + "$");

    let new_questions = []
    for(let i=0; i<outputs.length; i++){
        let output = outputs[i];
        let question = gather_questions[i];
        let finish_reason = output.finish_reason;
        let message = output.message;
        try{
            let new_question = await postprocess_answer(finish_reason, message, question);
            if(new_question != null)
                new_questions.push(new_question);
        }catch(e){
            console.log(e);
        }
    }

    fs.writeFileSync(params.output_path, JSON.stringify(new_questions));
}

export { main };

// GPT-4o mini: $0.1981 for 3516 questions