import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get("pdf") as File;

    if (!file) {
      return NextResponse.json(
        { error: "No PDF file provided" },
        { status: 400 }
      );
    }

    // Convert PDF to text using a simple approach
    // For production, you might want to use a more robust PDF library
    const arrayBuffer = await file.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    // Simple text extraction (this is a placeholder)
    // In a real implementation, you would use a PDF parsing library
    // For now, we'll return a placeholder or use pdftotext
    const text = await extractTextFromPDF(buffer);

    return NextResponse.json({ text });
  } catch (error) {
    console.error("Error extracting PDF text:", error);
    return NextResponse.json(
      { error: "Failed to extract text from PDF" },
      { status: 500 }
    );
  }
}

async function extractTextFromPDF(buffer: Buffer): Promise<string> {
  // Simple implementation using external pdftotext command
  // You could also use libraries like pdf-parse or pdf2pic
  
  const { exec } = require("child_process");
  const fs = require("fs");
  const path = require("path");
  const { promisify } = require("util");
  
  const execAsync = promisify(exec);
  
  // Create temporary file
  const tempDir = "/tmp";
  const tempPdfPath = path.join(tempDir, `temp-${Date.now()}.pdf`);
  const tempTxtPath = path.join(tempDir, `temp-${Date.now()}.txt`);
  
  try {
    // Write buffer to temporary PDF file
    fs.writeFileSync(tempPdfPath, buffer);
    
    // Extract text using pdftotext
    await execAsync(`pdftotext "${tempPdfPath}" "${tempTxtPath}"`);
    
    // Read extracted text
    const text = fs.readFileSync(tempTxtPath, "utf-8");
    
    // Clean up temporary files
    fs.unlinkSync(tempPdfPath);
    fs.unlinkSync(tempTxtPath);
    
    return text;
  } catch (error) {
    // Clean up on error
    try {
      if (fs.existsSync(tempPdfPath)) fs.unlinkSync(tempPdfPath);
      if (fs.existsSync(tempTxtPath)) fs.unlinkSync(tempTxtPath);
    } catch (cleanupError) {
      console.error("Cleanup error:", cleanupError);
    }
    
    throw new Error(`PDF text extraction failed: ${error}`);
  }
}