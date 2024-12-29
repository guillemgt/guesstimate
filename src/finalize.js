import zlib from 'zlib';
import fs from 'fs';

/* =============================
    Main
   ============================= */

async function main(params = {
    "input_path": "data/get_metadata.json",
    "output_path": "data/data.json.gz",
}) {
    const questions = JSON.parse(fs.readFileSync(params.input_path));

    let new_questions = []
    for(let question of questions){
        new_questions.push({
            "topic": question.topic,
            "description": [
                question.description_base,
                question.description_date == "null" ? null : question.description_date,
                question.description_unit == "null" ? null : question.description_unit
            ],
            "answer": question.answer,
            "excerpt": question.found_excerpt,
            // "category": question.category,
        });
    }

    const jsonString = JSON.stringify(new_questions);

    // Compress the JSON data using gzip
    zlib.gzip(jsonString, (err, buffer) => {
        if (err) {
            console.error('Error compressing data:', err);
            return;
        }
        
        // Write the compressed data to a file
        fs.writeFileSync(params.output_path, buffer);
        console.log('Compressed JSON data written to', params.output_path);
    });
}

export { main };