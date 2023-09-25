"use strict";

window.onload = function () {
    // Buttons to clear inserted file:
    function button_param(button){
        button.innerHTML = "Clear inserted file";
        button.style.fontFamily = 'Arial';
        button.style.fontSize = '1em';
        button.className = "btn btn-outline-dark btn-sm mt-2";
        button.setAttribute('type','button');
    }

    let input_file_div = document.getElementById('div_id_input_file');
    let input_file_button = document.createElement("button");
    button_param(input_file_button);
    input_file_div.appendChild(input_file_button);

    input_file_button.addEventListener("click", () => {
        document.getElementById("id_input_file").value = null;
    })


    let taxid_map_div = document.getElementById('div_id_taxid_map');
    let taxid_map_button = document.createElement("button");
    button_param(taxid_map_button);
    taxid_map_div.appendChild(taxid_map_button);

    taxid_map_button.addEventListener("click", () => {
        document.getElementById("id_taxid_map").value = null;
        document.getElementById('id_taxid').disabled = false;
    })

    let parse_seqids = document.getElementById('id_parse_seqids');
    let taxid = document.getElementById('id_taxid');
    let taxid_map = document.getElementById('id_taxid_map');

    taxid.addEventListener("change", () => {
        if(taxid.value.length === 0){
            taxid_map.disabled = false;
        }
        else{
            taxid_map.disabled = "true";
        }
    });

    taxid_map.addEventListener("change", () => {
        if(taxid_map.files.length === 0){
            taxid.disabled = false;
        }
        else{
            taxid.disabled = "true";
            parse_seqids.required = true;

        }
    });

};

