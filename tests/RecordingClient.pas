/// A JSON client that records the last request and answers with a fixed body, for the test programs
unit RecordingClient;

{$I mormot.defines.inc}

interface

uses
  mormot.core.base,
  mormot.net.client;

type
  TRecordingClient = class(TJsonClientAbstract)
  public
    SentMethod, SentAction, SentBody, Answer: RawUtf8;
    Calls: integer;
    function GetCookies: RawUtf8; override;
    procedure SetCookies(const Value: RawUtf8); override;
    function GetDefaultHeaders: RawUtf8; override;
    procedure SetDefaultHeaders(const Value: RawUtf8); override;
    function Http: IHttpClient; override;
    procedure AddDefaultHeader(const Name, Value: RawUtf8); override;
    function Connected: string; override;
    procedure RawRequest(const Method, Action, InType, InBody, InHeaders: RawUtf8;
      var Response: TJsonResponse); override;
  end;

var
  Failures: integer;

procedure Expect(ok: boolean; const what: string);

implementation

function TRecordingClient.GetCookies: RawUtf8;
begin
  result := '';
end;

procedure TRecordingClient.SetCookies(const Value: RawUtf8);
begin
end;

function TRecordingClient.GetDefaultHeaders: RawUtf8;
begin
  result := '';
end;

procedure TRecordingClient.SetDefaultHeaders(const Value: RawUtf8);
begin
end;

function TRecordingClient.Http: IHttpClient;
begin
  result := nil;
end;

procedure TRecordingClient.AddDefaultHeader(const Name, Value: RawUtf8);
begin
end;

function TRecordingClient.Connected: string;
begin
  result := 'recorder';
end;

procedure TRecordingClient.RawRequest(const Method, Action, InType, InBody, InHeaders: RawUtf8;
  var Response: TJsonResponse);
begin
  inc(Calls);
  SentMethod := Method;
  SentAction := Action;
  SentBody := InBody;
  Response.Status := 200;
  Response.Method := Method;
  Response.Url := Action;
  Response.Content := Answer;
  UniqueString(Response.Content); // mORMot parses the answer in place, so it must not be a literal
end;

procedure Expect(ok: boolean; const what: string);
begin
  if not ok then
  begin
    writeln('FAIL: ', what);
    inc(Failures);
  end;
end;

end.
