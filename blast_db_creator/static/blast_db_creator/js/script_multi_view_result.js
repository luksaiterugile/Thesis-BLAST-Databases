"use strict";

// Function to activate button
function activate_button(object){
    object.classList.remove("disable");
    object.classList.add("active");
    object.disabled = false;
}

// Function to deactivate button
function deactivate_button(object){
    object.classList.remove("active");
    object.classList.add("disable");
    object.disabled = true; 
}

// Function to retrieve id of currently uncollapsed accordion
var accordionItems = document.querySelectorAll('.accordion-item');

// If one of accordions uncollapsed, do tasks.
accordionItems.forEach(function(item) {
  item.addEventListener('shown.bs.collapse', function(event) {
    let item = event.target;

    if(!item.classList.contains('show')){
        return; // Do nothing if collapsed
    }
    else{
        var itemId = item.getAttribute('aria-labelledby');
    }

    // Retrieve buttons associated with this collapse
    let prevButton = document.querySelector("#prev" + itemId);
    let nextButton = document.querySelector("#next" + itemId);
    let firstButton = document.querySelector("#first" + itemId);
    let lastButton = document.querySelector("#last" + itemId);

    // Retrieve current section number and all section number span's
    let current_section_span = document.querySelector("#section_num" + itemId);
    let max_section_span = document.querySelector("#all_section_num" + itemId);

    // Retrieve all objects associated with this dbs collapse 
    const all_objects = document.querySelectorAll(`[id$="${itemId}"]`);

    // Loop through all objects and retrieve only those 
    // who have class="section"
    const sections = [];
    for (const object of all_objects) {
        if (object.classList.contains("section")) {
            sections.push(object);
        }
    }
    
    // Retrieve number of sections and insert it to max_section_span
    let num_of_sections = sections.length;
    max_section_span.textContent = num_of_sections;
    
    // Insert current section to current_section_span span
    let current_section = 0;
    current_section_span.value = current_section + 1;

    // Initial status of sections
    sections[current_section].classList.add("active");
    deactivate_button(prevButton);
    
    // Functions to account for user made changes while clicking on
    // buttons and inserting page number
    function change_section(event){
        if(event.target.id == firstButton.id){
            sections[current_section].classList.remove("active");
            sections[0].classList.add("active");
            current_section = 0;
            current_section_span.value = current_section + 1;
            deactivate_button(prevButton);
            activate_button(nextButton);
        }
        else if(event.target.id == lastButton.id){
            sections[current_section].classList.remove("active");
            sections[num_of_sections-1].classList.add("active");
            current_section = num_of_sections-1;
            current_section_span.value = num_of_sections;
            deactivate_button(nextButton);
            activate_button(prevButton);

        }
        else if(event.target.id == prevButton.id){
            sections[current_section].classList.remove("active");
            if(current_section > 0 || current_section + 1 == num_of_sections){
                current_section--;
                current_section_span.value = current_section + 1;
                sections[current_section].classList.add("active");
                activate_button(prevButton);
                activate_button(nextButton)
            }
            if(current_section == 0){
                deactivate_button(prevButton);
            }
            if(current_section + 1  == num_of_sections){
                deactivate_button(nextButton);
            }

        }
        else if(event.target.id == nextButton.id){
            sections[current_section].classList.remove("active");
            if(current_section >= 0 || current_section + 1 < num_of_sections){
                current_section++;
                current_section_span.value = current_section + 1;
                sections[current_section].classList.add("active");
                activate_button(prevButton);
                activate_button(nextButton);
                if(current_section + 1 == num_of_sections){
                    deactivate_button(nextButton);
                }
                if(current_section == 0){
                    deactivate_button(prevButton);
                }
            }

        }
        else if(event.target.id == current_section_span.id){
            let wanted_section = current_section_span.value - 1;
            sections[current_section].classList.remove("active")

            if(wanted_section == 0){
                sections[wanted_section].classList.add("active");
                deactivate_button(prevButton);
                activate_button(nextButton);
                current_section = wanted_section;
            }
            else if(wanted_section + 1 == num_of_sections){
                sections[wanted_section].classList.add("active");
                deactivate_button(nextButton);
                accordionItems(prevButton);
                current_section = wanted_section;
            }
            else if(wanted_section > 0 && wanted_section + 1 < num_of_sections){
                sections[wanted_section].classList.add("active");
                activate_button(nextButton);
                activate_button(prevButton);
                current_section = wanted_section;
            }
            else{
                alert("Such section does not exist!");
                sections[current_section].classList.add("active");
                current_section_span.value = current_section + 1;
                if(current_section == 0){
                    deactivate_button(prevButton);
                    activate_button(nextButton);
                }
                else if(current_section + 1 == num_of_sections){
                    deactivate_button(nextButton);
                    activate_button(prevButton);
                }
                else if(current_section > 0 && 
                    current_section + 1 < num_of_sections){
                    activate_button(nextButton);
                    activate_button(prevButton);
                }
            }
        }
    }

    // Merging two event listeners into one
    nextButton.addEventListener("click", change_section);
    prevButton.addEventListener("click", change_section);
    firstButton.addEventListener("click", change_section);
    lastButton.addEventListener("click", change_section);
    current_section_span.addEventListener("change", change_section);
  });
});
