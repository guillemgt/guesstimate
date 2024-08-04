import path from 'path';
import fs from 'fs';

/* =============================
    Completing unfinished JSONs
   ============================= */

import {completeTruncatedJSON} from "./general/json.js"


/* =============================
    Calling APIs
   ============================= */

import { do_openai_requests, compute_price } from "./general/openai.js"
import { wrap_prompt } from "./general/utils.js"


/* =============================
    Main
   ============================= */

async function postprocess_answer(finish_reason, output_text, topic){

    if(finish_reason != "stop" && finish_reason != "length"){
        console.log("Finish reason for stage 1 is not stop or length")
        console.log(finish_reason)
        console.log(input_usage, "IT,", output_usage, "OT,", compute_price(input_usage, output_usage) + "$")
        return
    }

    let primitive_questions = {};
    let questions = [];

    try{
        primitive_questions = JSON.parse(output_text);
    } catch {
        let malformed_questions = completeTruncatedJSON(output_text, true);
        if(!malformed_questions){
            console.log("Couldn't parse JSON.");
            console.log(output_text);
            return;
        }

        for(let i=0; i<malformed_questions.length; i++){
            let keys = Object.keys(malformed_questions[i]);
            for(let j=0; j<keys.length; j++){
                primitive_questions[keys[j]] = malformed_questions[i][keys[j]];
            }
        }

        if(!primitive_questions){
            console.log("Couldn't parse JSON.");
            console.log(output_text);
            return;
        }
    }

    try {
        for(let i=Object.keys(primitive_questions).length-1; i>=0; i--){
            let description = Object.keys(primitive_questions)[i];
            try {
                let excerpt = primitive_questions[description][0];
                let answer = primitive_questions[description][1];
                questions.push({
                    topic: topic,
                    description: description,
                    answer: answer,
                    reported_excerpt: excerpt,
                })
            } catch(e) {
                continue;
            }
        }
    } catch {
        console.log("JSON was malformed")
    }
        
    return questions;
}

async function main(params = {
    "input_path": "data/wikipedia_dumps/",
    "output_path": "data/retrieve_quantities.json",
    "log_path": "data/logs/retrieve_quantities/",
    "system_prompt_path": "prompts/retrieve_quantities_system.txt",
    "temperature": 0.3,
}) {
    // Read the wikipedia dumps
    let dir_wikidump = params.input_path

    // Read the files in the wikipedia dumps folder
    let topics = fs.readdirSync(dir_wikidump).map(x => x.replace(".txt", ""));

    // Form the prompts
    const system_prompt = fs.readFileSync(params.system_prompt_path, 'utf8');

    let prompts = []
    let prompt_topics = []
    for(let topic of topics){
        let wikidump_path = path.join(dir_wikidump, topic + ".txt")

        if(!fs.existsSync(wikidump_path)){
            console.log("Article '" + topic + "' not found");
            continue;
        }
        
        let wikipedia_text = fs.readFileSync(wikidump_path, 'utf8');

        let prompt = await wrap_prompt(wikipedia_text, system_prompt, []);

        prompts.push(prompt);
        prompt_topics.push(topic);
    }



    fs.mkdirSync(params.log_path, { recursive: true });
    
    const batch_call_id = "gather_questions";
    let [outputs, input_usage, output_usage] = await do_openai_requests(
        prompts,
        batch_call_id,
        params.log_path,
        {
            force_json: true,
            use_batch_api: true,
            temperature: params.temperature
        }
    );
    console.log(input_usage, "IT,", output_usage, "OT,", compute_price(input_usage, output_usage) + "$");

    let questions = [];
    for(let i=0; i<outputs.length; i++){
        let output = outputs[i];
        if(output === undefined){
            continue;
        }
        let finish_reason = output.finish_reason;
        let message = output.message;
        questions = questions.concat(await postprocess_answer(finish_reason, message, prompt_topics[i]));
    }

    fs.writeFileSync(params.output_path, JSON.stringify(questions));
}

export { main };

// GPT-4o mini: $0.8535 for 1002 topics