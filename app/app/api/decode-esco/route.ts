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
    return NextResponse.json(
      { error: "Failed to decode ESCO data" },
      { status: 500 }
    );
  }
}

async function decodeEscoItems(urls: string[], type: "skills" | "occupations"): Promise<EscoItem[]> {
  try {
    const csvFileName = type === "skills" ? "skills.csv" : "occupations.csv";
    const csvPath = path.join(process.cwd(), "..", "api", "esco_skill_extractor", "data", csvFileName);
    
    const csvContent = fs.readFileSync(csvPath, "utf-8");
    const lines = csvContent.split("\n");
    
    const escoMap = new Map<string, string>();
    
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;
      
      const firstCommaIndex = line.indexOf(',');
      if (firstCommaIndex === -1) continue;
      
      const id = line.substring(0, firstCommaIndex).trim();
      const description = line.substring(firstCommaIndex + 1).trim();
      
      const cleanDescription = description.replace(/^"/, "").replace(/"$/, "");
      escoMap.set(id, cleanDescription);
    }
    
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
    return urls.map(url => ({
      id: url,
      description: url.split("/").pop() || url,
    }));
  }
}

function extractMainName(description: string): string {
  if (!description) return "Unknown";
  
  const words = description.split(/\s+/);
  if (words.length === 0) return "Unknown";
  
  let result = words[0];
  
  for (let i = 1; i < Math.min(3, words.length); i++) {
    const word = words[i];
    const lowerWord = word.toLowerCase();
    
    if (['the', 'and', 'or', 'manage', 'coordinate', 'perform', 'conduct', 'develop', 'create'].includes(lowerWord)) {
      break;
    }
    
    if (['of', 'for', 'with', 'in', 'on', 'to', 'as', 'at', 'by'].includes(lowerWord)) {
      break;
    }
    
    if (word.length > 1) {
      result += ` ${word}`;
    }
  }
  
  result = result.trim();
  if (result) {
    result = result.charAt(0).toUpperCase() + result.slice(1);
  }
  
  return result || "Unknown";
}