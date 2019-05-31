<?php

namespace App\Http\Controllers;

use \Cache;

use App\Guild;
use Illuminate\Http\Request;

class GuildController extends Controller
{
    /**
     * Display a listing of the resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function index(Request $request)
    {
        $guilds;
        if (Cache::has('guilds')) {
            $guilds = Cache::get('guilds');
        } else {
            $guilds = Cache::remember('guilds', (60 * 24), function () {
                return Guild::with('affiliates', 'affiliatedTo')->get();
            });
        }

        $filterString = $request->query('q');
        if ($filterString) {
            $guilds = $guilds->filter(function ($value, $key) use ($filterString) {
                return stripos($value->name, $filterString) > -1;
            });
        }

        return response()->json($guilds);
    }

}
