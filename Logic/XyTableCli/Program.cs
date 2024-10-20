using SkiaSharp;
using TwinCAT.Ads;

static void WriteSegment(AdsClient adsClient, uint hStart, uint hEnd, Span<SKPoint> points, SKPathVerb verb)
{
    int dataIndex = adsClient.ReadAny<int>(hEnd);
    int count = 0;
    switch(verb)
    {
        case SKPathVerb.Line:
            adsClient.WriteSymbolAsync($"ZGlobal.Com.Unit.XyTable.Subscribe.Segments.Data[{dataIndex}].Verb", 1, CancellationToken.None).Wait();
            count = 2;
            break;
        case SKPathVerb.Quad:
            adsClient.WriteSymbolAsync($"ZGlobal.Com.Unit.XyTable.Subscribe.Segments.Data[{dataIndex}].Verb", 2, CancellationToken.None).Wait();
            count = 5;
            break;
    }

    for (var i = 0; i < count; i++)
    {
        adsClient.WriteSymbolAsync($"ZGlobal.Com.Unit.XyTable.Subscribe.Segments.Data[{dataIndex}].Points[{i}].X", points[i].X, CancellationToken.None).Wait();
        adsClient.WriteSymbolAsync($"ZGlobal.Com.Unit.XyTable.Subscribe.Segments.Data[{dataIndex}].Points[{i}].Y", points[i].Y, CancellationToken.None).Wait();
    }

    dataIndex = dataIndex >= 200 ? 0 : dataIndex + 1;
    while (adsClient.ReadAny<int>(hStart) == dataIndex || (dataIndex == 200 && adsClient.ReadAny<int>(hStart) == 0))
        Thread.Sleep(1000);

    adsClient.WriteAny(hEnd, dataIndex);
}

static SKPoint BezierPoint(Span<SKPoint> controlPoints, float t)
{
    float u = 1 - t;
    float tt = t * t;
    float uu = u * u;
    float uuu = uu * u;
    float ttt = tt * t;

    return new SKPoint(
        uu * controlPoints[0].X + 2 * u * t * controlPoints[1].X + tt * controlPoints[2].X, 
        uu * controlPoints[0].Y + 2 * u * t * controlPoints[1].Y + tt * controlPoints[2].Y);
}

static void Clear()
{
    Console.Clear();
    Console.WriteLine("Type something (press 'Esc' to exit, 'Enter' to reset):");
}

var textWidth = 0.0f;
Clear();
using (var adsClient = new AdsClient())
{
    adsClient.Connect(851);
    var hStart = adsClient.CreateVariableHandle("ZGlobal.Com.Unit.XyTable.Subscribe.Segments.Start");
    var hEnd = adsClient.CreateVariableHandle("ZGlobal.Com.Unit.XyTable.Subscribe.Segments.End");
    
    while (true)
    {
        var keyInfo = Console.ReadKey(intercept: true);

        if (keyInfo.Key == ConsoleKey.Escape)
            break;

        if (keyInfo.Key == ConsoleKey.Enter)
        {
            textWidth = 0;
            Clear();
        }

        Console.Write(keyInfo.KeyChar.ToString());

        using (var paint = new SKPaint())
        {
            paint.TextSize = 50;
            paint.Color = SKColors.Black;
            paint.IsAntialias = true;
            
            var charWidth = paint.MeasureText(keyInfo.KeyChar.ToString());
            var path = paint.GetTextPath(keyInfo.KeyChar.ToString(), textWidth, 50);
            textWidth += charWidth;

            var it = path.CreateIterator(false);
            var points = new Span<SKPoint>(new SKPoint[4]);
            SKPathVerb verb;
            while ((verb = it.Next(points)) != SKPathVerb.Done)
            {
                if (verb == SKPathVerb.Line)
                {
                    WriteSegment(adsClient, hStart, hEnd, points, verb);
                }
                else if (verb == SKPathVerb.Quad)
                {
                    var segmentPoints = new Span<SKPoint>(new SKPoint[5]);
                    segmentPoints[0] = points[0];
                    segmentPoints[1] = BezierPoint(points, 0.25f);
                    segmentPoints[2] = BezierPoint(points, 0.5f);
                    segmentPoints[3] = BezierPoint(points, 0.75f);
                    segmentPoints[4] = points[2];
                    WriteSegment(adsClient, hStart, hEnd, segmentPoints, verb);
                }
            }
        }
    }
}


