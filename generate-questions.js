import fs from 'fs';
import path from 'path';

const args = process.argv.slice(2);
const namedArgs = {};

const GLOBAL_CONFIG = JSON.parse(fs.readFileSync(args.length > 0 ? args[0] : "config.json", 'utf8'));
fs.mkdirSync(GLOBAL_CONFIG.run_path, { recursive: true });

let last_output_path = null;

for(let i=0; i<GLOBAL_CONFIG.pipeline.length; i++){
    let step = GLOBAL_CONFIG.pipeline[i];

    let filename = step.action;
    let params = step.params;

    if(params["output_path"])
        params["output_path"] = path.join(GLOBAL_CONFIG.run_path, params["output_path"]);
    if(params["log_path"])
        params["log_path"] = path.join(GLOBAL_CONFIG.run_path, params["log_path"]);
    if(params["wikidump_path"])
        params["wikidump_path"] = path.join(GLOBAL_CONFIG.run_path, params["wikidump_path"]);

    if(params["input_path"]){
        params["input_path"] = path.join(GLOBAL_CONFIG.run_path, params["input_path"]);
    }else if(last_output_path){
        params["input_path"] = last_output_path;
    }else if(i == 0){
        params["input_path"] = GLOBAL_CONFIG.topics_file;
    }
    last_output_path = params["output_path"];

    console.log("Running", filename, "with", params);

    const module = await import(`./${filename}`);
    await module.main(params);
}