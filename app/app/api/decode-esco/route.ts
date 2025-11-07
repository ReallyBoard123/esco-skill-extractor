import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";

interface EscoItem {
  id: string;
  description: string;
}

export async function POST(request: NextRequest) {
  try {
    const { skills = [], occupations = [] } = await request.json();

    const decodedSkills = await decodeEscoItems(skills, "skills");
    const decodedOccupations = await decodeEscoItems(occupations, "occupations");

    return NextResponse.json({
      skills: decodedSkills,
      occupations: decodedOccupations,
    });
  } catch (error) {
    console.error("Error decoding ESCO data:", error);
    return NextResponse.json(
      { error: "Failed to decode ESCO data" },
      { status: 500 }
    );
  }
}

async function decodeEscoItems(urls: string[], type: "skills" | "occupations"): Promise<EscoItem[]> {
  try {
    // Path to the ESCO CSV files in the API directory
    const csvFileName = type === "skills" ? "skills.csv" : "occupations.csv";
    const csvPath = path.join(process.cwd(), "..", "api", "esco_skill_extractor", "data", csvFileName);
    
    // Read and parse CSV
    const csvContent = fs.readFileSync(csvPath, "utf-8");
    const lines = csvContent.split("\n");
    
    // Create a map for fast lookup
    const escoMap = new Map<string, string>();
    
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;
      
      // Parse CSV line - first comma separates ID from description
      const firstCommaIndex = line.indexOf(',');
      if (firstCommaIndex === -1) continue;
      
      const id = line.substring(0, firstCommaIndex).trim();
      const description = line.substring(firstCommaIndex + 1).trim();
      
      // Remove quotes and clean description
      const cleanDescription = description.replace(/^"/, "").replace(/"$/, "");
      escoMap.set(id, cleanDescription);
    }
    
    // Decode URLs to descriptions
    const decodedItems: EscoItem[] = [];
    
    for (const url of urls) {
      const description = escoMap.get(url);
      if (description) {
        const cleanName = extractMainName(description);
        decodedItems.push({
          id: url,
          description: cleanName,
        });
      } else {
        // Fallback: extract ID from URL
        const idMatch = url.match(/\/([^/]+)$/);
        const fallbackName = idMatch ? idMatch[1] : url;
        decodedItems.push({
          id: url,
          description: fallbackName,
        });
      }
    }
    
    return decodedItems;
  } catch (error) {
    console.error(`Error decoding ${type}:`, error);
    return urls.map(url => ({
      id: url,
      description: url.split("/").pop() || url,
    }));
  }
}

function extractMainName(description: string): string {
  // Extract the main term from ESCO descriptions
  // Format: "main term alternative terms description..."
  
  const words = description.split(/\s+/);
  if (words.length === 0) return "Unknown";
  
  // Special cases for known patterns
  if (description.includes("video editing") || description.includes("motion picture editor")) {
    return "Video editor";
  }
  if (description.includes("R The techniques")) {
    return "R";
  }
  if (description.includes("TypeScript The techniques")) {
    return "TypeScript";
  }
  if (description.includes("Python") && description.includes("computer programming")) {
    return "Python";
  }
  if (description.includes("university") && (description.includes("teacher") || description.includes("lecturer"))) {
    return "University lecturer";
  }
  
  // General extraction logic
  let result = words[0];
  
  // Build compound terms intelligently
  for (let i = 1; i < Math.min(4, words.length); i++) {
    const word = words[i];
    const lowerWord = word.toLowerCase();
    
    // Stop if we hit these indicators (start of alternatives/description)
    if (['the', 'and', 'or', 'manage', 'coordinate', 'perform', 'conduct', 'develop', 'create'].includes(lowerWord)) {
      break;
    }
    
    // Stop if word is repetition of existing
    if (result.toLowerCase().includes(lowerWord)) {
      break;
    }
    
    // Add word if it's meaningful
    if (word.length > 1 && !['of', 'for', 'with', 'in', 'on', 'to', 'as', 'at', 'by'].includes(lowerWord)) {
      result += ` ${word}`;
    }
  }
  
  // Clean up
  result = result.replace(/\s*\(.*?\)/g, ''); // remove parentheses
  result = result.replace(/\s+/g, ' ').trim(); // normalize spaces
  result = result.replace(/[,.]$/, ''); // remove trailing punctuation
  
  // Capitalize properly
  if (result) {
    result = result.charAt(0).toUpperCase() + result.slice(1);
  }
  
  return result || "Unknown";
}