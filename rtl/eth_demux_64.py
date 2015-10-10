#!/usr/bin/env python
"""eth_demux_64

Generates an Ethernet demux with the specified number of ports

Usage: eth_demux_64 [OPTION]...
  -?, --help     display this help and exit
  -p, --ports    specify number of ports
  -n, --name     specify module name
  -o, --output   specify output file name
"""

from __future__ import print_function

import io
import sys
import getopt
import math
from jinja2 import Template

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "?n:p:o:", ["help", "name=", "ports=", "output="])
        except getopt.error as msg:
             raise Usage(msg)
        # more code, unchanged  
    except Usage as err:
        print(err.msg, file=sys.stderr)
        print("for help use --help", file=sys.stderr)
        return 2

    ports = 4
    name = None
    out_name = None

    # process options
    for o, a in opts:
        if o in ('-?', '--help'):
            print(__doc__)
            sys.exit(0)
        if o in ('-p', '--ports'):
            ports = int(a)
        if o in ('-n', '--name'):
            name = a
        if o in ('-o', '--output'):
            out_name = a

    if name is None:
        name = "eth_demux_64_{0}".format(ports)

    if out_name is None:
        out_name = name + ".v"

    print("Opening file '%s'..." % out_name)

    try:
        out_file = open(out_name, 'w')
    except Exception as ex:
        print("Error opening \"%s\": %s" %(out_name, ex.strerror), file=sys.stderr)
        exit(1)

    print("Generating {0} port Ethernet demux {1}...".format(ports, name))

    select_width = int(math.ceil(math.log(ports, 2)))

    t = Template(u"""/*

Copyright (c) 2014 Alex Forencich

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

*/

// Language: Verilog 2001

`timescale 1ns / 1ps

/*
 * Ethernet {{n}} port demultiplexer (64 bit datapath)
 */
module {{name}}
(
    input  wire        clk,
    input  wire        rst,
    
    /*
     * Ethernet frame input
     */
    input  wire        input_eth_hdr_valid,
    output wire        input_eth_hdr_ready,
    input  wire [47:0] input_eth_dest_mac,
    input  wire [47:0] input_eth_src_mac,
    input  wire [15:0] input_eth_type,
    input  wire [63:0] input_eth_payload_tdata,
    input  wire [7:0]  input_eth_payload_tkeep,
    input  wire        input_eth_payload_tvalid,
    output wire        input_eth_payload_tready,
    input  wire        input_eth_payload_tlast,
    input  wire        input_eth_payload_tuser,
    
    /*
     * Ethernet frame outputs
     */
{%- for p in ports %}
    output wire        output_{{p}}_eth_hdr_valid,
    input  wire        output_{{p}}_eth_hdr_ready,
    output wire [47:0] output_{{p}}_eth_dest_mac,
    output wire [47:0] output_{{p}}_eth_src_mac,
    output wire [15:0] output_{{p}}_eth_type,
    output wire [63:0] output_{{p}}_eth_payload_tdata,
    output wire [7:0]  output_{{p}}_eth_payload_tkeep,
    output wire        output_{{p}}_eth_payload_tvalid,
    input  wire        output_{{p}}_eth_payload_tready,
    output wire        output_{{p}}_eth_payload_tlast,
    output wire        output_{{p}}_eth_payload_tuser,
{% endfor %}
    /*
     * Control
     */
    input  wire        enable,
    input  wire [{{w-1}}:0]  select
);

reg [{{w-1}}:0] select_reg = 0, select_next;
reg frame_reg = 0, frame_next;

reg input_eth_hdr_ready_reg = 0, input_eth_hdr_ready_next;
reg input_eth_payload_tready_reg = 0, input_eth_payload_tready_next;
{% for p in ports %}
reg output_{{p}}_eth_hdr_valid_reg = 0, output_{{p}}_eth_hdr_valid_next;
{%- endfor %}
reg [47:0] output_eth_dest_mac_reg = 0, output_eth_dest_mac_next;
reg [47:0] output_eth_src_mac_reg = 0, output_eth_src_mac_next;
reg [15:0] output_eth_type_reg = 0, output_eth_type_next;

// internal datapath
reg [63:0] output_eth_payload_tdata_int;
reg [7:0]  output_eth_payload_tkeep_int;
reg        output_eth_payload_tvalid_int;
reg        output_eth_payload_tready_int = 0;
reg        output_eth_payload_tlast_int;
reg        output_eth_payload_tuser_int;
wire       output_eth_payload_tready_int_early;

assign input_eth_hdr_ready = input_eth_hdr_ready_reg;
assign input_eth_payload_tready = input_eth_payload_tready_reg;
{% for p in ports %}
assign output_{{p}}_eth_hdr_valid = output_{{p}}_eth_hdr_valid_reg;
assign output_{{p}}_eth_dest_mac = output_eth_dest_mac_reg;
assign output_{{p}}_eth_src_mac = output_eth_src_mac_reg;
assign output_{{p}}_eth_type = output_eth_type_reg;
{% endfor %}
// mux for output control signals
reg current_output_eth_hdr_valid;
reg current_output_eth_hdr_ready;
reg current_output_tvalid;
reg current_output_tready;
always @* begin
    case (select_reg)
{%- for p in ports %}
        {{w}}'d{{p}}: begin
            current_output_eth_hdr_valid = output_{{p}}_eth_hdr_valid;
            current_output_eth_hdr_ready = output_{{p}}_eth_hdr_ready;
            current_output_tvalid = output_{{p}}_eth_payload_tvalid;
            current_output_tready = output_{{p}}_eth_payload_tready;
        end
{%- endfor %}
    endcase
end

always @* begin
    select_next = select_reg;
    frame_next = frame_reg;

    input_eth_hdr_ready_next = input_eth_hdr_ready_reg & ~input_eth_hdr_valid;
    input_eth_payload_tready_next = 0;

{%- for p in ports %}
    output_{{p}}_eth_hdr_valid_next = output_{{p}}_eth_hdr_valid_reg & ~output_{{p}}_eth_hdr_ready;
{%- endfor %}
    output_eth_dest_mac_next = output_eth_dest_mac_reg;
    output_eth_src_mac_next = output_eth_src_mac_reg;
    output_eth_type_next = output_eth_type_reg;

    if (frame_reg) begin
        if (input_eth_payload_tvalid & input_eth_payload_tready) begin
            // end of frame detection
            frame_next = ~input_eth_payload_tlast;
        end
    end else if (enable & input_eth_hdr_valid & ~current_output_eth_hdr_valid & ~current_output_tvalid) begin
        // start of frame, grab select value
        frame_next = 1;
        select_next = select;

        input_eth_hdr_ready_next = 1;

        case (select)
{%- for p in ports %}
            {{w}}'d{{p}}: output_{{p}}_eth_hdr_valid_next = 1;
{%- endfor %}
        endcase
        output_eth_dest_mac_next = input_eth_dest_mac;
        output_eth_src_mac_next = input_eth_src_mac;
        output_eth_type_next = input_eth_type;
    end

    input_eth_payload_tready_next = output_eth_payload_tready_int_early & frame_next;

    output_eth_payload_tdata_int = input_eth_payload_tdata;
    output_eth_payload_tkeep_int = input_eth_payload_tkeep;
    output_eth_payload_tvalid_int = input_eth_payload_tvalid & input_eth_payload_tready;
    output_eth_payload_tlast_int = input_eth_payload_tlast;
    output_eth_payload_tuser_int = input_eth_payload_tuser;
end

always @(posedge clk) begin
    if (rst) begin
        select_reg <= 0;
        frame_reg <= 0;
        input_eth_hdr_ready_reg <= 0;
        input_eth_payload_tready_reg <= 0;
{%- for p in ports %}
        output_{{p}}_eth_hdr_valid_reg <= 0;
{%- endfor %}
        output_eth_dest_mac_reg <= 0;
        output_eth_src_mac_reg <= 0;
        output_eth_type_reg <= 0;
    end else begin
        select_reg <= select_next;
        frame_reg <= frame_next;
        input_eth_hdr_ready_reg <= input_eth_hdr_ready_next;
        input_eth_payload_tready_reg <= input_eth_payload_tready_next;
{%- for p in ports %}
        output_{{p}}_eth_hdr_valid_reg <= output_{{p}}_eth_hdr_valid_next;
{%- endfor %}
        output_eth_dest_mac_reg <= output_eth_dest_mac_next;
        output_eth_src_mac_reg <= output_eth_src_mac_next;
        output_eth_type_reg <= output_eth_type_next;
    end
end

// output datapath logic
reg [63:0] output_eth_payload_tdata_reg = 0;
reg [7:0]  output_eth_payload_tkeep_reg = 0;
{%- for p in ports %}
reg        output_{{p}}_eth_payload_tvalid_reg = 0;
{%- endfor %}
reg        output_eth_payload_tlast_reg = 0;
reg        output_eth_payload_tuser_reg = 0;

reg [63:0] temp_eth_payload_tdata_reg = 0;
reg [7:0]  temp_eth_payload_tkeep_reg = 0;
reg        temp_eth_payload_tvalid_reg = 0;
reg        temp_eth_payload_tlast_reg = 0;
reg        temp_eth_payload_tuser_reg = 0;
{% for p in ports %}
assign output_{{p}}_eth_payload_tdata = output_eth_payload_tdata_reg;
assign output_{{p}}_eth_payload_tkeep = output_eth_payload_tkeep_reg;
assign output_{{p}}_eth_payload_tvalid = output_{{p}}_eth_payload_tvalid_reg;
assign output_{{p}}_eth_payload_tlast = output_eth_payload_tlast_reg;
assign output_{{p}}_eth_payload_tuser = output_eth_payload_tuser_reg;
{% endfor %}
// enable ready input next cycle if output is ready or if there is space in both output registers or if there is space in the temp register that will not be filled next cycle
assign output_eth_payload_tready_int_early = current_output_tready | (~temp_eth_payload_tvalid_reg & ~current_output_tvalid) | (~temp_eth_payload_tvalid_reg & ~output_eth_payload_tvalid_int);

always @(posedge clk) begin
    if (rst) begin
        output_eth_payload_tdata_reg <= 0;
        output_eth_payload_tkeep_reg <= 0;
{%- for p in ports %}
        output_{{p}}_eth_payload_tvalid_reg <= 0;
{%- endfor %}
        output_eth_payload_tlast_reg <= 0;
        output_eth_payload_tuser_reg <= 0;
        output_eth_payload_tready_int <= 0;
        temp_eth_payload_tdata_reg <= 0;
        temp_eth_payload_tkeep_reg <= 0;
        temp_eth_payload_tvalid_reg <= 0;
        temp_eth_payload_tlast_reg <= 0;
        temp_eth_payload_tuser_reg <= 0;
    end else begin
        // transfer sink ready state to source
        output_eth_payload_tready_int <= output_eth_payload_tready_int_early;

        if (output_eth_payload_tready_int) begin
            // input is ready
            if (current_output_tready | ~current_output_tvalid) begin
                // output is ready or currently not valid, transfer data to output
                output_eth_payload_tdata_reg <= output_eth_payload_tdata_int;
                output_eth_payload_tkeep_reg <= output_eth_payload_tkeep_int;
                case (select_reg)
{%- for p in ports %}
                    {{w}}'d{{p}}: output_{{p}}_eth_payload_tvalid_reg <= output_eth_payload_tvalid_int;
{%- endfor %}
                endcase
                output_eth_payload_tlast_reg <= output_eth_payload_tlast_int;
                output_eth_payload_tuser_reg <= output_eth_payload_tuser_int;
            end else begin
                // output is not ready, store input in temp
                temp_eth_payload_tdata_reg <= output_eth_payload_tdata_int;
                temp_eth_payload_tkeep_reg <= output_eth_payload_tkeep_int;
                temp_eth_payload_tvalid_reg <= output_eth_payload_tvalid_int;
                temp_eth_payload_tlast_reg <= output_eth_payload_tlast_int;
                temp_eth_payload_tuser_reg <= output_eth_payload_tuser_int;
            end
        end else if (current_output_tready) begin
            // input is not ready, but output is ready
            output_eth_payload_tdata_reg <= temp_eth_payload_tdata_reg;
            output_eth_payload_tkeep_reg <= temp_eth_payload_tkeep_reg;
            case (select_reg)
{%- for p in ports %}
                {{w}}'d{{p}}: output_{{p}}_eth_payload_tvalid_reg <= temp_eth_payload_tvalid_reg;
{%- endfor %}
            endcase
            output_eth_payload_tlast_reg <= temp_eth_payload_tlast_reg;
            output_eth_payload_tuser_reg <= temp_eth_payload_tuser_reg;
            temp_eth_payload_tdata_reg <= 0;
            temp_eth_payload_tkeep_reg <= 0;
            temp_eth_payload_tvalid_reg <= 0;
            temp_eth_payload_tlast_reg <= 0;
            temp_eth_payload_tuser_reg <= 0;
        end
    end
end

endmodule

""")
    
    out_file.write(t.render(
        n=ports,
        w=select_width,
        name=name,
        ports=range(ports)
    ))
    
    print("Done")

if __name__ == "__main__":
    sys.exit(main())

