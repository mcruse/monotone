package com.cisco.ui.components.view
{
	import flash.net.FileReference;
	
	import mx.controls.Alert;
	import mx.controls.DataGrid;
	import mx.controls.dataGridClasses.DataGridColumn;
	import mx.core.Application;
	import mx.printing.FlexPrintJob;
	import mx.printing.PrintDataGrid;

	public class ExportDataGrid extends DataGrid
	{
		private var fileReference:FileReference;
		public function exportCSV(columns:Array=null):void {
			var requiredColumns:Array = columns;
			if ( requiredColumns == null || requiredColumns.length == 0 ) {
				requiredColumns = this.columns;
			}
			var headerFlag:Boolean=false;
			var firstHeaderFlag:Boolean = true;
			var csvString:String = "";
			var column:DataGridColumn

			for each ( column in requiredColumns ) {
				if ( firstHeaderFlag ) {
					firstHeaderFlag = false;
				} else {
					csvString += ",";
				}
				csvString += column.headerText;
			}

			for each ( var item:Object in collection ) {
				csvString += "\n";
				firstHeaderFlag = true;
				for each ( column in requiredColumns ) {
					if ( firstHeaderFlag ) {
						firstHeaderFlag = false;
					} else {
						csvString += ",";
					}
					csvString += "\"" + column.itemToLabel(item) + "\"";
				}
			}
			
			try {
				fileReference = new FileReference();
				fileReference.save(csvString,"logs.csv");
			} catch (ex:Error) {
				Alert.show("Please update the flash player to 10.0 or above do download this data");
			}
		}
		
		public function print():void {
			var printJob:FlexPrintJob = new FlexPrintJob();
			
			
			if (printJob.start()) {
				var printGrid:PrintDataGrid = new PrintDataGrid();
				printGrid.width = printJob.pageWidth;
				printGrid.height = printJob.pageHeight;
				printGrid.dataProvider = collection;
				printGrid.columns = columns;
				printGrid.visible = false;
				printGrid.includeInLayout = false;
				Application.application.addChild(printGrid);
				if(!printGrid.validNextPage) {
					printJob.addObject(printGrid);
				} else {
					printJob.addObject(printGrid);
				}
				
				while(true) {
					// Move the next page of data to the top of the print grid.
					printGrid.nextPage();
	
					if(!printGrid.validNextPage) {
						// This is the last page; queue it and exit the print loop.
						printJob.addObject(printGrid);
						break;
					} else {
						printJob.addObject(printGrid);
					}
				}
				Application.application.removeChild(printGrid);
				printJob.send();
			}
		}

	}
}