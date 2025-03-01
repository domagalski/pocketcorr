
function pfb_fir_2048ch_2i_core_config(this_block)

  % Revision History:
  %
  %   15-May-2012  (10:50 hours):
  %     Original code was machine generated by Xilinx's System Generator after parsing
  %     /scratch/zaki/workspace/roachfengine/pfb_fir_1024ch_core.vhd
  %
  %

  this_block.setTopLevelLanguage('VHDL');

  this_block.setEntityName('pfb_fir_2048ch_2i_core_ip_struct');

  % System Generator has to assume that your entity  has a combinational feed through; 
  %   if it  doesn't, then comment out the following line:
  %this_block.tagAsCombinational;

  this_block.addSimulinkInport('sync');
  this_block.addSimulinkInport('pol0_in0');
  this_block.addSimulinkInport('pol0_in1');
  this_block.addSimulinkInport('pol1_in0');
  this_block.addSimulinkInport('pol1_in1');

  this_block.addSimulinkOutport('sync_out');
  this_block.addSimulinkOutport('pol0_out0');
  this_block.addSimulinkOutport('pol0_out1');
  this_block.addSimulinkOutport('pol1_out0');
  this_block.addSimulinkOutport('pol1_out1');

  pol0_out0_port = this_block.port('pol0_out0');
  pol0_out0_port.setType('Fix_18_17');
  pol0_out1_port = this_block.port('pol0_out1');
  pol0_out1_port.setType('Fix_18_17');
  pol1_out0_port = this_block.port('pol1_out0');
  pol1_out0_port.setType('Fix_18_17');
  pol1_out1_port = this_block.port('pol1_out1');
  pol1_out1_port.setType('Fix_18_17');

  sync_out_port = this_block.port('sync_out');
  sync_out_port.setType('UFix_1_0');

  % -----------------------------
  if (this_block.inputTypesKnown)
    % do input type checking, dynamic output type and generic setup in this code block.

    if (this_block.port('pol0_in0').width ~= 8);
      this_block.setError('Input data type for port "pol0_in0" must have width=8.');
    end

    if (this_block.port('pol0_in1').width ~= 8);
      this_block.setError('Input data type for port "pol0_in1" must have width=8.');
    end

    if (this_block.port('pol1_in0').width ~= 8);
      this_block.setError('Input data type for port "pol1_in0" must have width=8.');
    end

    if (this_block.port('pol1_in1').width ~= 8);
      this_block.setError('Input data type for port "pol1_in1" must have width=8.');
    end

    if (this_block.port('sync').width ~= 32);
      this_block.setError('Input data type for port "sync" must have width=32.');
    end

    %this_block.port('sync').useHDLVector(false);

  end  % if(inputTypesKnown)
  % -----------------------------

  % -----------------------------
   if (this_block.inputRatesKnown)
     setup_as_single_rate(this_block,'clk_1','ce_1')
   end  % if(inputRatesKnown)
  % -----------------------------

    % (!) Set the inout port rate to be the same as the first input 
    %     rate. Change the following code if this is untrue.
    uniqueInputRates = unique(this_block.getInputRates);


  % Add addtional source files as needed.
  %  |-------------
  %  | Add files in the order in which they should be compiled.
  %  | If two files "a.vhd" and "b.vhd" contain the entities
  %  | entity_a and entity_b, and entity_a contains a
  %  | component of type entity_b, the correct sequence of
  %  | addFile() calls would be:
  %  |    this_block.addFile('b.vhd');
  %  |    this_block.addFile('a.vhd');
  %  |-------------

  %    this_block.addFile('');
  %    this_block.addFile('');
  %this_block.addFile('pfb_fir_2048ch_2i_core/sysgen/pfb_fir_2048ch_2i_core.vhd');
  this_block.addFile('pfb_fir_2048ch_2i_core.vhd');


return;


% ------------------------------------------------------------

function setup_as_single_rate(block,clkname,cename) 
  inputRates = block.inputRates; 
  uniqueInputRates = unique(inputRates); 
  if (length(uniqueInputRates)==1 & uniqueInputRates(1)==Inf) 
    block.addError('The inputs to this block cannot all be constant.'); 
    return; 
  end 
  if (uniqueInputRates(end) == Inf) 
     hasConstantInput = true; 
     uniqueInputRates = uniqueInputRates(1:end-1); 
  end 
  if (length(uniqueInputRates) ~= 1) 
    block.addError('The inputs to this block must run at a single rate.'); 
    return; 
  end 
  theInputRate = uniqueInputRates(1); 
  for i = 1:block.numSimulinkOutports 
     block.outport(i).setRate(theInputRate); 
  end 
  block.addClkCEPair(clkname,cename,theInputRate); 
  return; 

% ------------------------------------------------------------

