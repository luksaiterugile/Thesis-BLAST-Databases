"use strict";

window.onload = function () {
    var query_file = document.getElementById('id_query_file');
    var gilist = document.getElementById("id_gilist");
    var seqidlist = document.getElementById('id_seqidlist');
    var negative_gilist =  document.getElementById('id_negative_gilist');
    var negative_seqidlist =  document.getElementById('id_negative_seqidlist');
    var taxidlist =  document.getElementById('id_taxidlist');
    var negative_taxidlist =  document.getElementById('id_negative_taxidlist');
    var taxids =  document.getElementById('id_taxids');
    var negative_taxids =  document.getElementById('id_negative_taxids');

    function button_param(button){
        button.innerHTML = "Clear inserted file";
        button.style.fontFamily = 'Arial';
        button.style.fontSize = '1em';
        button.className = "btn btn-outline-dark btn-sm";
        button.style.marginTop = '8px';
        button.setAttribute('type','button');
    }

    // Creating buttons to clear file inputs
    var query_file_div = document.getElementById('div_id_query_file');
    var query_button = document.createElement("button");
    button_param(query_button);
    query_file_div.appendChild(query_button);

    var gilist_div = document.getElementById('div_id_gilist');
    var gilist_button = document.createElement("button");
    button_param(gilist_button);
    gilist_div.appendChild(gilist_button);

    var seqidlist_div = document.getElementById('div_id_seqidlist');
    var seqidlist_button = document.createElement("button");
    button_param(seqidlist_button);
    seqidlist_div.appendChild(seqidlist_button);

    var negative_gilist_div = document.getElementById('div_id_negative_gilist');
    var negative_gilist_button = document.createElement("button");
    button_param(negative_gilist_button);
    negative_gilist_div.appendChild(negative_gilist_button);

    var negative_seqidlist_div = 
        document.getElementById('div_id_negative_seqidlist');
    var negative_seqidlist_button = document.createElement("button");
    button_param(negative_seqidlist_button);
    negative_seqidlist_div.appendChild(negative_seqidlist_button);

    var taxidlist_div = document.getElementById('div_id_taxidlist');
    var taxidlist_button = document.createElement("button");
    button_param(taxidlist_button);
    taxidlist_div.appendChild(taxidlist_button);

    var negative_taxidlist_div = 
        document.getElementById('div_id_negative_taxidlist');
    var negative_taxidlist_button = document.createElement("button");
    button_param(negative_taxidlist_button);
    negative_taxidlist_div.appendChild(negative_taxidlist_button);

    // Adding event listeners to buttons. When button is clicked, file field
    // becomes empty

    query_button.addEventListener('click', () => {
        query_file.value = null;
    })

    gilist_button.addEventListener('click', () => {
        gilist.value = null;

        seqidlist.disabled = false;
        negative_gilist.disabled = false;
        negative_seqidlist.disabled = false;
        taxids.disabled = false;
        negative_taxids.disabled = false;
        taxidlist.disabled = false;
        negative_taxidlist.disabled = false;

        seqidlist_button.style.display = 'block';
        negative_gilist_button.style.display = 'block';
        negative_seqidlist_button.style.display = 'block';
        taxidlist_button.style.display = 'block';
        negative_taxidlist_button.style.display = 'block';
    })

    seqidlist_button.addEventListener('click', () => {
        seqidlist.value = null;

        gilist.disabled = false;
        negative_gilist.disabled = false;
        negative_seqidlist.disabled = false;
        taxids.disabled = false;
        negative_taxids.disabled = false;
        taxidlist.disabled = false;
        negative_taxidlist.disabled = false;

        gilist_button.style.display = 'block';
        negative_gilist_button.style.display = 'block';
        negative_seqidlist_button.style.display = 'block';
        taxidlist_button.style.display = 'block';
        negative_taxidlist_button.style.display = 'block';
    })

    negative_gilist_button.addEventListener('click', () => {
        negative_gilist.value = null;

        gilist.disabled = false;
        seqidlist.disabled = false;
        negative_seqidlist.disabled = false;
        taxids.disabled = false;
        negative_taxids.disabled = false;
        taxidlist.disabled = false;
        negative_taxidlist.disabled = false;

        gilist_button.style.display = 'block';
        seqidlist_button.style.display = 'block';
        negative_seqidlist_button.style.display = 'block';
        taxidlist_button.style.display = 'block';
        negative_taxidlist_button.style.display = 'block';
    })

    negative_seqidlist_button.addEventListener('click', () => {
        negative_seqidlist.value = null;

        gilist.disabled = false;
        seqidlist.disabled = false;
        negative_gilist.disabled = false;
        taxids.disabled = false;
        negative_taxids.disabled = false;
        taxidlist.disabled = false;
        negative_taxidlist.disabled = false;

        gilist_button.style.display = 'block';
        seqidlist_button.style.display = 'block';
        negative_gilist.style.display = 'block';
        taxidlist_button.style.display = 'block';
        negative_taxidlist_button.style.display = 'block';
    })

    taxidlist_button.addEventListener('click', () => {
        taxidlist.value = null;

        gilist.disabled = false;
        seqidlist.disabled = false;
        negative_gilist.disabled = false;
        negative_seqidlist.disabled = false;
        taxids.disabled = false;
        negative_taxids.disabled = false;
        negative_taxidlist.disabled = false;

        gilist_button.style.display = 'block';
        seqidlist_button.style.display = 'block';
        negative_gilist_button.style.display = 'block';
        negative_seqidlist_button.style.display = 'block';
        negative_taxidlist_button.style.display = 'block';
    })

    negative_taxidlist_button.addEventListener('click', () => {
        negative_taxidlist.value = null;

        gilist.disabled = false;
        seqidlist.disabled = false;
        negative_gilist.disabled = false;
        negative_seqidlist.disabled = false;
        taxids.disabled = false;
        negative_taxids.disabled = false;
        taxidlist.disabled = false;
        
        gilist_button.style.display = 'block';
        seqidlist_button.style.display = 'block';
        negative_gilist_button.style.display = 'block';
        negative_seqidlist_button.style.display = 'block';
        taxidlist_button.style.display = 'block';
    })


    // Change placeholders based on selected value
    var task = document.getElementById('id_task');

    if(task.value == 'megablast'){
        document.getElementById('id_word_size')
            .placeholder='28, if not provided';
    }
    else if(task.value === 'dc-megablast'){
        document.getElementById('id_word_size')
            .placeholder='11, if not provided';
    }
    else if(task.value === 'blastn'){
        document.getElementById('id_word_size')
            .placeholder='11, if not provided';
    }
    else if(task.value === 'blastn-short'){
        document.getElementById('id_word_size')
            .placeholder='7, if not provided';
    }
    else if(task.value === 'rmblastn'){
        document.getElementById('id_word_size').placeholder='';
    }

    // Changing placeholder text if select value has changed
    task.addEventListener("change", stateHandle);

    function stateHandle() {
        if(task.value === 'dc-megablast') {            
            document.getElementById('id_word_size')
                .placeholder='11, if not provided';
        }
        else if(task.value === 'megablast') {
            document.getElementById('id_word_size')
                .placeholder='28, if not provided';
        }
        else if(task.value === 'blastn'){
            document.getElementById('id_word_size')
                .placeholder='11, if not provided';
        }
        else if(task.value === 'blastn-short'){
            document.getElementById('id_word_size')
                .placeholder='7, if not provided';
        }
        else if(task.value == 'rmblastn'){
            document.getElementById('id_word_size').placeholder='';
        }
    }

    // Disabling and enabling fields when fields are incompatible
    gilist.addEventListener("change", stateHandle_Incompatible_1);
    seqidlist.addEventListener("change", stateHandle_Incompatible_2);
    negative_gilist.addEventListener("change", stateHandle_Incompatible_3);
    negative_seqidlist.addEventListener("change", stateHandle_Incompatible_4);
    taxids.addEventListener("change", stateHandle_Incompatible_5);
    negative_taxids.addEventListener("change", stateHandle_Incompatible_6);
    taxidlist.addEventListener("change", stateHandle_Incompatible_7);
    negative_taxidlist.addEventListener("change", stateHandle_Incompatible_8);

    function stateHandle_Incompatible_1(){
        seqidlist.disabled = "true";
        taxids.disabled = "true";
        taxidlist.disabled = "true";
        negative_gilist.disabled = "true";
        negative_seqidlist.disabled = "true";
        negative_taxids.disabled = "true";
        negative_taxidlist.disabled = "true";

        // Hide clear buttons
        seqidlist_button.style.display = 'none';
        taxidlist_button.style.display = 'none';
        negative_gilist_button.style.display = 'none';
        negative_seqidlist_button.style.display = 'none';
        negative_taxidlist_button.style.display = 'none';
    }

    function stateHandle_Incompatible_2(){
        gilist.disabled = "true";
        taxids.disabled = "true";
        taxidlist.disabled = "true";
        negative_gilist.disabled = "true";
        negative_seqidlist.disabled = "true";
        negative_taxids.disabled = "true";
        negative_taxidlist.disabled = "true";

        // Hide clear buttons
        gilist_button.style.display = 'none';
        taxidlist_button.style.display = 'none';
        negative_gilist_button.style.display = 'none';
        negative_seqidlist_button.style.display = 'none';
        negative_taxidlist_button.style.display = 'none';

    }

    function stateHandle_Incompatible_3(){
        gilist.disabled = "true";
        seqidlist.disabled = "true";
        taxids.disabled = "true";
        taxidlist.disabled = "true";
        negative_seqidlist.disabled = "true";
        negative_taxids.disabled = "true";
        negative_taxidlist.disabled = "true";

        // Hide clear buttons
        gilist_button.style.display = 'none';
        seqidlist_button.style.display = 'none';
        taxidlist_button.style.display = 'none';
        negative_seqidlist_button.style.display = 'none';
        negative_taxidlist_button.style.display = 'none';

    }

    function stateHandle_Incompatible_4(){
        gilist.disabled = "true";
        seqidlist.disabled = "true";
        negative_gilist.disabled = "true";
        taxids.disabled = "true";
        negative_taxids.disabled = "true";
        taxidlist.disabled = "true";
        negative_taxidlist.disabled = "true";

        // Hide clear buttons
        gilist_button.style.display = 'none';
        seqidlist_button.style.display = 'none';
        negative_gilist_button.style.display = 'none';
        taxidlist_button.style.display = 'none';
        negative_taxidlist_button.style.display = 'none';

    }

    function stateHandle_Incompatible_5(){
        gilist.disabled = "true";
        seqidlist.disabled = "true";
        taxidlist.disabled = "true";
        negative_gilist.disabled = "true";
        negative_seqidlist.disabled = "true";
        negative_taxids.disabled = "true";
        negative_taxidlist.disabled = "true";

        // Hide clear buttons
        gilist_button.style.display = 'none';
        seqidlist_button.style.display = 'none';
        taxidlist_button.style.display = 'none';
        negative_gilist_button.style.display = 'none';
        negative_seqidlist_button.style.display = 'none';
        negative_taxidlist_button.style.display = 'none';

        if(taxids.value.length == 0){
            gilist.disabled = false;
            seqidlist.disabled = false;
            taxidlist.disabled = false;
            negative_gilist.disabled = false;
            negative_seqidlist.disabled = false;
            negative_taxids.disabled = false;
            negative_taxidlist.disabled = false;
        }
    }

    function stateHandle_Incompatible_6(){
        gilist.disabled = "true";
        seqidlist.disabled = "true";
        taxids.disabled = "true";
        taxidlist.disabled = "true";
        negative_gilist.disabled = "true";
        negative_seqidlist.disabled = "true";
        negative_taxidlist.disabled = "true";

        // Hide clear buttons
        gilist_button.style.display = 'none';
        seqidlist_button.style.display = 'none';
        taxidlist_button.style.display = 'none';
        negative_gilist_button.style.display = 'none';
        negative_seqidlist_button.style.display = 'none';
        negative_taxidlist_button.style.display = 'none';

        if(negative_taxids.value.length == 0){
            gilist.disabled = false;
            seqidlist.disabled = false;
            taxids.disabled = false;
            taxidlist.disabled = false;
            negative_gilist.disabled = false;
            negative_seqidlist.disabled = false;
            negative_taxidlist.disabled = false;
        }
    }

    function stateHandle_Incompatible_7(){
        gilist.disabled = "true";
        seqidlist.disabled = "true";
        taxids.disabled = "true";
        negative_gilist.disabled = "true";
        negative_seqidlist.disabled = "true";
        negative_taxids.disabled = "true";
        negative_taxidlist.disabled = "true";

        // Hide clear buttons
        gilist_button.style.display = 'none';
        seqidlist_button.style.display = 'none';
        negative_gilist_button.style.display = 'none';
        negative_seqidlist_button.style.display = 'none';
        negative_taxidlist_button.style.display = 'none';
    }

    function stateHandle_Incompatible_8(){
        gilist.disabled = "true";
        seqidlist.disabled = "true";
        taxids.disabled = "true";
        taxidlist.disabled = "true";
        negative_gilist.disabled = "true";
        negative_seqidlist.disabled = "true";
        negative_taxids.disabled = "true";

        // Hide clear buttons
        gilist_button.style.display = 'none';
        seqidlist_button.style.display = 'none';
        taxidlist_button.style.display = 'none';
        negative_gilist_button.style.display = 'none';
        negative_seqidlist_button.style.display = 'none';
    }
};
