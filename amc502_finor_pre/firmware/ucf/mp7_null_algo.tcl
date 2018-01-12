# Area constraints for MP7 null algo

## HB 2018-01-12: this constraint was moved to area_constraints.tcl (by JW). See directory "replacement_files".
#add_cells_to_pblock [get_pblock payload] payload

## Input ports finor
## HB 2016-11-30: only FMC0 used on AMC502 finor preview.
set_property IOB TRUE [get_ports FMC0_LA00_CC_P]
set_property IOB TRUE [get_ports FMC0_LA01_CC_P]
set_property IOB TRUE [get_ports FMC0_LA02_P]
set_property IOB TRUE [get_ports FMC0_LA03_P]
set_property IOB TRUE [get_ports FMC0_LA04_P]
set_property IOB TRUE [get_ports FMC0_LA05_P]
# Output ports
set_property IOB TRUE [get_ports FMC0_LA06_P]
set_property IOB TRUE [get_ports FMC0_LA07_P]
