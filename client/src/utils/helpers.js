/**
 * Extracts transcript from a YouTube video URL using Puppeteer
 * @param {string} url - YouTube video URL
 * @returns {Promise<string>} - Video transcript with timestamps
 */
export const getYouTubeTranscript = async (url) => {
  try {
    // Navigate to the video
    await page.goto(url, { waitUntil: 'networkidle0' });
    
    // Wait for the video player to load
    await page.waitForSelector('video', { timeout: 5000 });
    
    // Click the "More actions" button
    await page.click('button[aria-label="More actions"]');
    
    // Wait for menu and click "Show transcript"
    await page.waitForSelector('tp-yt-paper-item', { timeout: 2000 });
    const menuItems = await page.$$('tp-yt-paper-item');
    for (const item of menuItems) {
      const text = await item.evaluate(el => el.textContent);
      if (text.includes('Show transcript')) {
        await item.click();
        break;
      }
    }
    
    // Wait for transcript panel and extract text
    await page.waitForSelector('ytd-transcript-segment-renderer', { timeout: 3000 });
    const transcriptSegments = await page.$$('ytd-transcript-segment-renderer');
    
    let transcript = '';
    for (const segment of transcriptSegments) {
      const timeText = await segment.$eval('.segment-timestamp', el => el.textContent.trim());
      const contentText = await segment.$eval('.segment-text', el => el.textContent.trim());
      transcript += `${timeText} ${contentText}\n`;
    }
    
    return transcript;

  } catch (error) {
    console.error('Error extracting transcript:', error);
    if (error.message.includes('timeout')) {
      throw new Error('Timeout: Video or transcript elements not found. The video might be unavailable or may not have a transcript.');
    }
    throw error;
  }
};