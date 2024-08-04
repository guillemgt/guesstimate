import { config } from 'dotenv';
import fs from 'fs';
config();

import { SingleBar, Presets } from 'cli-progress';


import OpenAI from "openai";
const openai = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY
});

/* =============================
    Spinning wheel
   ============================= */

function withSpinner(text, asyncFunction) {
    return async function (...args) {
        const startTime = Date.now(); // Record the start time
        const spinner = ["\\", "|", "/", "-"];
        let i = 0;

        const loadingInterval = setInterval(() => {
            process.stdout.write(
                `\r${text} ${spinner[i]} ${getTimeElapsed(startTime)}`
            );
            i = (i + 1) % spinner.length;
        }, 100);

        try {
            const result = await asyncFunction.call(this, ...args); // Bind the context using .call(this)
            clearInterval(loadingInterval);
            process.stdout.write(
                "\r" + " ".repeat(process.stdout.columns || 80) + "\r"
            ); // Clear the line
            console.log("Operation completed in", getTimeElapsed(startTime));
            return result;
        } catch (error) {
            clearInterval(loadingInterval);
            process.stdout.write(
                "\r" + " ".repeat(process.stdout.columns || 80) + "\r"
            ); // Clear the line
            console.error("Error:", error);
            throw error;
        }
    };
}

// Function to calculate the time elapsed in a human-readable format
function getTimeElapsed(startTime) {
    const elapsedMilliseconds = Date.now() - startTime;
    const seconds = Math.floor(elapsedMilliseconds / 1000);
    return `${seconds}s`;
}



/* =============================
    OpenAI API
   ============================= */


const OPENAI_PRICES = {
    "gpt-4o": [5.00, 15.00],
    "gpt-4o-mini": [0.150, 0.600],
};
const OPENAI_MODEL = "gpt-4o-mini";

const do_openai_request = async function(prompt, temperature=0.3, force_json=true){
    const props = {
        model: OPENAI_MODEL,
        messages: prompt,
        temperature: temperature,
        top_p: 1,
        frequency_penalty: 0,
        presence_penalty: 0,
        max_tokens: null,
        stream: false,
        n: 1,
    };

    if (force_json) {
        props.response_format = {type: "json_object"}
    }


    
    let completion = await withSpinner("Waiting for OpenAI", () => openai.chat.completions.create(props,
        //{timeout: 20 * 1000}
    ))();

    let choice = completion.choices[0];

    return [choice.finish_reason, choice.message.content, completion.usage]
    // stop, ??, { prompt_tokens: 2946, completion_tokens: 732, total_tokens: 3678 }
}

const upload_file_to_openai = async function(file_path){
    const file = await openai.files.create({
        file: fs.createReadStream(file_path),
        purpose: "batch",
    });

    return file.id;
}

function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

const wait_for_openai_batch = async function(batch_id){
    const progressBar = new SingleBar({
        format: '{description} | {bar} | {percentage}% | {value}/{total} | ETA: {eta_formatted}'
    }, Presets.shades_classic);
    let started_bar = false;

    // Wait 10s at the start
    await wait(10*1000);

    while(true){
        let batch = await openai.batches.retrieve(batch_id);
        if(batch.status == "failed" || batch.status == "cancelled" || batch.status == "completed"){
            break;
        }

        if(started_bar){
            progressBar.update(batch.request_counts.completed+batch.request_counts.failed, {
                description: batch.status,
            });
        }else if(batch.request_counts.total > 0){
            progressBar.start(batch.request_counts.total, batch.request_counts.completed+batch.request_counts.failed, {
                description: batch.status,
            });
            started_bar = true;
        }

        await wait(60*1000);
    }

    progressBar.stop();
}

const do_openai_requests = async function(prompts, batch_call_id, log_dir, {force_json=false, use_batch_api=true, temperature=1.0, num_choices=1, max_tokens=null}){
    let input_usage = 0
    let output_usage = 0

    let all_generation_parameters = [];

    for(let i=0; i<prompts.length; i++){
        const prompt_messages = prompts[i];

        let generation_parameters = {
            model: OPENAI_MODEL,
            messages: prompt_messages,
            temperature: temperature,
            top_p: 1,
            frequency_penalty: 0,
            presence_penalty: 0,
            max_tokens: max_tokens,
            stream: false,
            n: num_choices,
        };

        if (force_json) {
            generation_parameters.response_format = {type: "json_object"}
        }

        all_generation_parameters.push(generation_parameters);
    }

    if(use_batch_api){
        // Get the data that must be in the file and save it as a .jsonl file
        let all_lines = []
        for(let i=0; i<all_generation_parameters.length; i++){
            let line = {
                "custom_id": batch_call_id + ":" + i,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": all_generation_parameters[i]
            };
            all_lines.push(JSON.stringify(line));
        }

        fs.writeFileSync(log_dir + "batch.jsonl", all_lines.join("\n"));

        // Upload the file to OpenAI
        const file_id = await upload_file_to_openai(log_dir + "batch.jsonl");

        let batch = await openai.batches.create({
            input_file_id: file_id,
            endpoint: "/v1/chat/completions",
            completion_window: "24h"
        });

        console.log("Waiting for OpenAI (batch_id=" + batch.id + ")");

        const output_raw = await wait_for_openai_batch(batch.id);

        console.log("OpenAI batch finished");

        batch = await openai.batches.retrieve(batch.id);

        if(batch.status != "completed"){
            return null;
        }
        
        const fileResponse = await openai.files.content(batch.output_file_id);
        const fileContents = await fileResponse.text();
        fs.writeFileSync(log_dir + "batch_output.jsonl", fileContents);


        // // DEBUG: For debugging
        // const fileContents = fs.readFileSync(log_dir + "batch_output.jsonl", 'utf8');


        // Read jsonl from fileContents
        let outputs = []
        const lines = fileContents.split("\n");
        for(let i=0; i<lines.length-1; i++){
            const line = lines[i];
            const response = JSON.parse(line);
            let _s = response.custom_id.split(":");
            const id = parseInt(_s[_s.length-1]);
            
            let output = [];
            for(let choice of response.response.body.choices){
                output.push({
                    "finish_reason": choice.finish_reason,
                    "message": choice.message.content
                });
            }
            if(output.length == 1){
                output = output[0];
            }
            outputs[id] = output;

            let usage = response.response.body.usage;
            input_usage += usage.prompt_tokens;
            output_usage += usage.completion_tokens;
        }

        return [outputs, input_usage, output_usage];

    }else{
        let outputs = [];
        for(let i=0; i<all_generation_parameters.length; i++){
            console.log(all_generation_parameters[i])
            let completion = await withSpinner("Waiting for OpenAI", () => openai.chat.completions.create(all_generation_parameters[i],
                //{timeout: 20 * 1000}
            ))();

            let output = [];
            for(let choice of completion.choices){
                output.push({
                    "finish_reason": choice.finish_reason,
                    "message": choice.message.content
                });
            }
            if(output.length == 1){
                output = output[0];
            }
            outputs.push(output);

            let usage = completion.usage;
            input_usage += usage.prompt_tokens;
            output_usage += usage.completion_tokens;
        }
        return [outputs, input_usage, output_usage];
    }
}

const compute_price = function(input_usage, output_usage, string=true){
    let [input_cost, output_cost] = OPENAI_PRICES[OPENAI_MODEL];
    let x = ((input_cost*input_usage+output_cost*output_usage)/1e6)
    x = Math.round(x * 1e4) / 1e4
    if(string) return x.toFixed(4)
    return x
}


export { do_openai_request, do_openai_requests, compute_price };