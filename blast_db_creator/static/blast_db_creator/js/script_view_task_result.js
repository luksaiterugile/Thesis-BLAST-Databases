"use strict";

// Script for moving between sections 
window.onload = function() {
    var sections = document.querySelectorAll(".section");
    var prevButton = document.querySelector(".previous");
    var nextButton = document.querySelector(".next");
    var how_many_sections = (sections.length - 1);
    var current_section = 0;
    var section_num = document.getElementById("section_number");
    var first_sectionButton = document.querySelector(".first");
    var last_sectionButton = document.querySelector(".last");
    var num_of_sections = document.getElementById("all_section_num");
    num_of_sections.innerHTML = how_many_sections + 1;
    section_num.min = current_section + 1;
    section_num.max = how_many_sections + 1;

    function activate_button(object){
        object.classList.remove("disable");
        object.classList.add("active");
        object.disabled = false;
    }

    function deactivate_button(object){
        object.classList.remove("active");
        object.classList.add("disable");
        object.disabled = true; 
    }

    // Initial status
    sections[current_section].classList.add("active");
    deactivate_button(prevButton);
    section_num.value = current_section + 1;

    if(how_many_sections == 0){
        deactivate_button(nextButton);
    }

    function change_section(event){
       if(event.target.id == "first"){
            sections[current_section].classList.remove("active");
            sections[0].classList.add("active");
            current_section = 0;
            section_num.value = current_section + 1;
            deactivate_button(prevButton);
            activate_button(nextButton);
        }
        else if(event.target.id == "last"){
            sections[current_section].classList.remove("active");
            sections[how_many_sections].classList.add("active");
            current_section = how_many_sections;
            section_num.value = how_many_sections + 1;
            deactivate_button(nextButton);
            activate_button(prevButton);
        }
        else if(event.target.id == "prev"){
            sections[current_section].classList.remove("active");
            if(current_section > 0 || current_section <= how_many_sections){
                current_section--;
                section_num.value = current_section + 1;
                sections[current_section].classList.add("active");
                activate_button(prevButton);
                activate_button(nextButton);
                if(current_section == 0){
                    deactivate_button(prevButton);
                }
            }
        }
        else if(event.target.id == "next"){
            sections[current_section].classList.remove("active");
            if(current_section >= 0 || current_section < how_many_sections){
                current_section++;
                section_num.value = current_section + 1;
                sections[current_section].classList.add("active");
                activate_button(prevButton);
                activate_button(nextButton);
                if(current_section == how_many_sections){
                    deactivate_button(nextButton);
                }
            }
        }
        else if(event.target.id == "section_number"){
            var wanted_section = section_num.value - 1;
            sections[current_section].classList.remove("active");
            if(wanted_section == 0){
                sections[wanted_section].classList.add("active");
                deactivate_button(prevButton);
                activate_button(nextButton);
                current_section = wanted_section;
            }
            else if(wanted_section == how_many_sections){
                sections[wanted_section].classList.add("active");
                deactivate_button(nextButton);
                activate_button(prevButton);
                current_section = wanted_section;
            }
            else if(wanted_section > 0 && wanted_section < how_many_sections){
                sections[wanted_section].classList.add("active");
                activate_button(nextButton);
                activate_button(prevButton);
                current_section = wanted_section;
            }
            else{
                alert("Such section does not exist!");
                sections[current_section].classList.add("active");
                section_num.value = current_section + 1;
                if(current_section == 0){
                    deactivate_button(prevButton);
                    activate_button(nextButton);
                }
                else if(current_section == how_many_sections){
                    deactivate_button(nextButton);
                    activate_button(prevButton);
                }
                else if(current_section > 0 && 
                    current_section < how_many_sections){
                    activate_button(nextButton);
                    activate_button(prevButton);
                }
            }
        } 
    }
    

    // Merging two event listeners into one
    nextButton.addEventListener("click", change_section);
    prevButton.addEventListener("click", change_section);
    first_sectionButton.addEventListener("click", change_section);
    last_sectionButton.addEventListener("click", change_section);
    section_num.addEventListener("change", change_section);
};
