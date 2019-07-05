<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class EmailListRequest extends FormRequest
{
    /**
     * Get the validation rules that apply to the request.
     *
     * @return array
     */
    public function rules()
    {
        return [
            'emails' => 'required|array|max:10',
            'emails.*.email' => 'required|email',
        ];
    }

    public function messages()
    {
        return [
            'emails.*.email' => 'List of recipients contains an invalid email address: :input',
        ];
    }

    /**
     * Prepare the data for validation.
     *
     * @return void
     */
    protected function prepareForValidation()
    {
        $this->merge([
            'emails' => $this->extractEmailAddresses($this->emails),
        ]);
    }

    private function extractEmailAddresses($input)
    {
        return collect(explode(',', $input))
            ->filter(function ($line) {
                return $line != '' && !ctype_space($line);
            })->map(function ($line) {
                // Attempt to match line in the format "FirstName Surname" <Email@Adress.com>
                if (preg_match('/(?:"?([^"^\s]*)\s?([^"]*)?"?\s)?(?:<?(.+@[^>]+)>?)/', $line, $matches)) {
                    return ['email' => $matches[3], 'forename' => $matches[1], 'surname' => $matches[2]];
                } else {
                    return ['email' => $line];
                }
            })->toArray();
    }
}
